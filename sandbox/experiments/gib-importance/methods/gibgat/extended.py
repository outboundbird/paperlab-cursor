"""Stage-2 extension of GIBGAT for the gib-importance experiment.

Per the 2026-06-16 extension regime spec
(`log/2026-06-16-critic-code-review-and-coder-extension.md`),
this module **inherits / composes** the audited Stage-1 method at
``vault_code_dir("GIBGAT")/method.py``; it does not copy or
hand-reimplement the base method.

Inheritance summary
-------------------
- ``ExtendedGIBGATLayer`` extends Stage-1 ``GIBGATLayer``:
  * widens the attention parameter from ``[max_hop, heads, 2*F]``
    to ``[max_hop, heads, 2*F + 1]`` to admit a scalar edge feature
    in the candidate logit ``(Z̃_v ⊕ e_{vu} ⊕ Z̃_u) a^T``
    (`design.md` §5.1, extension #2);
  * overrides ``_structure_and_pool`` to thread ``edge_index`` /
    ``edge_attr`` and emit per-directed-edge AIB-Bern KL telemetry;
  * inherits ``_transform``, ``_gaussian_sample``, and
    ``MixtureGaussianPrior`` unchanged.
- ``ExtendedGIBGAT`` extends Stage-1 ``Method``:
  * delegates state setup to ``super().__init__`` (inheriting
    ``self.dropout``, ``self.heads``, ``self.num_layers`` etc.),
    then **replaces** ``self.layers`` with ``ExtendedGIBGATLayer``
    instances (uniform width, no last-layer collapse, all using
    ``struct_mode="bern"``) and adds a graph-level readout
    (``_global_sum_pool`` + ``self.graph_head``);
  * overrides ``forward`` for graph classification: returns
    ``(graph_logits, reg_info, per_edge_kl, per_node_ixz)``
    instead of the base node-level ``(h, reg_info)``.

Anything not listed above is inherited.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import RelaxedBernoulli

from methods.gibgat._vault_import import load_gibgat_method_module

_vault = load_gibgat_method_module()
GIBGATLayer = _vault.GIBGATLayer
Method = _vault.Method
build_hop_pools = _vault.build_hop_pools
_bernoulli_kl = _vault._bernoulli_kl


def build_edge_lookup(edge_index: torch.Tensor) -> Dict[Tuple[int, int], int]:
    """Map directed edge ``(src, dst)`` to row index in ``edge_index``."""
    lookup: Dict[Tuple[int, int], int] = {}
    row, col = edge_index[0], edge_index[1]
    for idx in range(edge_index.shape[1]):
        lookup[(int(row[idx]), int(col[idx]))] = idx
    return lookup


class ExtendedGIBGATLayer(GIBGATLayer):
    """Stage-1 ``GIBGATLayer`` + edge-feature attention + per-edge KL telemetry."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        heads: int = 8,
        concat: bool = True,
        max_hop: int = 1,
        k_samples: int = 3,
        temperature: float = 0.1,
        bern_prior_alpha: float = 0.5,
        negative_slope: float = 0.2,
        use_reparam: bool = False,
        prior_components: int = 100,
        val_use_mean: bool = True,
    ) -> None:
        super().__init__(
            in_channels=in_channels,
            out_channels=out_channels,
            heads=heads,
            concat=concat,
            struct_mode="bern",
            max_hop=max_hop,
            k_samples=k_samples,
            temperature=temperature,
            bern_prior_alpha=bern_prior_alpha,
            negative_slope=negative_slope,
            use_reparam=use_reparam,
            prior_components=prior_components,
            val_use_mean=val_use_mean,
        )
        # Widen attention parameter by +1 to admit a scalar edge feature
        # in the candidate logit (design.md §5.1, extension #2). Replaces
        # the parent's att Parameter; weight is unchanged.
        att_width = 2 * self.out_neurons + 1
        self.att = nn.Parameter(torch.empty(max_hop, heads, att_width))
        nn.init.xavier_uniform_(self.att)

    def _structure_and_pool(  # type: ignore[override]
        self,
        z_tilde: torch.Tensor,
        hop_pools: List[List[List[int]]],
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        edge_lookup: Dict[Tuple[int, int], int],
        training: bool,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        num_nodes = z_tilde.shape[0]
        num_edges = edge_index.shape[1]
        device = z_tilde.device
        dtype = z_tilde.dtype

        z_bar = torch.zeros(num_nodes, self.heads, self.out_neurons, device=device, dtype=dtype)
        structure_kl = torch.zeros((), device=device, dtype=dtype)
        edge_kl = torch.zeros(num_edges, device=device, dtype=dtype)
        edge_kl_count = torch.zeros(num_edges, device=device, dtype=dtype)

        use_mean = (not training) and self.val_use_mean

        for v in range(num_nodes):
            for t in range(1, self.max_hop + 1):
                pool = hop_pools[v][t]
                if not pool:
                    continue

                pool_idx = torch.tensor(pool, device=device, dtype=torch.long)
                z_u = z_tilde[pool_idx]
                z_v = z_tilde[v].unsqueeze(0).expand(len(pool), -1, -1)

                edge_feats = torch.zeros(len(pool), 1, device=device, dtype=dtype)
                edge_indices: List[Optional[int]] = []
                for i, u in enumerate(pool):
                    u_int = int(u)
                    eidx = edge_lookup.get((v, u_int))
                    if eidx is None:
                        eidx = edge_lookup.get((u_int, v))
                    edge_indices.append(eidx)
                    if eidx is not None:
                        edge_feats[i, 0] = edge_attr[eidx, 0]

                edge_feats = edge_feats.unsqueeze(1).expand(-1, self.heads, -1)
                concat = torch.cat([z_v, edge_feats, z_u], dim=-1)
                logits = (concat * self.att[t - 1]).sum(dim=-1)
                logits = F.leaky_relu(logits, self.negative_slope)

                probs = torch.sigmoid(logits).clamp(0.01, 0.99)
                kl_per_candidate = _bernoulli_kl(probs, self.bern_prior_alpha)
                structure_kl = structure_kl + kl_per_candidate.sum()

                for i, eidx in enumerate(edge_indices):
                    if eidx is not None:
                        edge_kl[eidx] += kl_per_candidate[i].sum()
                        edge_kl_count[eidx] += 1.0

                if use_mean:
                    for h in range(self.heads):
                        z_bar[v, h] += (probs[:, h].unsqueeze(-1) * z_u[:, h]).sum(dim=0)
                else:
                    temp = torch.tensor([self.temperature], device=device, dtype=probs.dtype)
                    for h in range(self.heads):
                        ph = probs[:, h]
                        if training:
                            relaxed = RelaxedBernoulli(temp, probs=ph).rsample()
                            z_bar[v, h] += (relaxed.unsqueeze(-1) * z_u[:, h]).sum(dim=0)
                        else:
                            z_bar[v, h] += (ph.unsqueeze(-1) * z_u[:, h]).sum(dim=0)

        edge_kl = edge_kl / edge_kl_count.clamp(min=1.0)
        return z_bar, structure_kl, edge_kl

    def forward(  # type: ignore[override]
        self,
        z: torch.Tensor,
        hop_pools: List[List[List[int]]],
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        edge_lookup: Dict[Tuple[int, int], int],
        training: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z_tilde = self._transform(z)
        z_bar, structure_kl, edge_kl = self._structure_and_pool(
            z_tilde, hop_pools, edge_index, edge_attr, edge_lookup, training,
        )
        z_core, ixz = self._gaussian_sample(z_bar, training)

        if self.concat:
            out = z_core.reshape(z_core.shape[0], self.heads * self.out_channels)
        else:
            out = z_core.mean(dim=1)

        return out, ixz, structure_kl, edge_kl


class ExtendedGIBGAT(Method):
    """Graph-classification GIBGAT extending node-level Stage-1 ``Method``."""

    def __init__(
        self,
        *,
        in_channels: int = 1,
        num_classes: int = 2,
        hidden_channels: int = 8,
        heads: int = 8,
        num_layers: int = 2,
        max_hop: int = 1,
        k_samples: int = 3,
        temperature: float = 0.1,
        bern_prior_alpha: float = 0.5,
        negative_slope: float = 0.2,
        dropout: float = 0.6,
        xib_layer_indices: Tuple[int, ...] = (0,),
        prior_components: int = 100,
        val_use_mean: bool = True,
    ) -> None:
        super().__init__(
            in_channels=in_channels,
            num_classes=num_classes,
            struct_mode="bern",
            hidden_channels=hidden_channels,
            heads=heads,
            num_layers=num_layers,
            max_hop=max_hop,
            k_samples=k_samples,
            temperature=temperature,
            bern_prior_alpha=bern_prior_alpha,
            negative_slope=negative_slope,
            dropout=dropout,
            xib_layer_indices=xib_layer_indices,
            prior_components=prior_components,
            val_use_mean=val_use_mean,
        )
        # Replace parent's heterogeneous-width layers (last layer collapses
        # to num_classes/heads=1) with uniform-width edge-aware layers
        # suitable for a graph-level readout.
        self.layers = nn.ModuleList()
        for layer_idx in range(num_layers):
            in_ch = in_channels if layer_idx == 0 else hidden_channels * heads
            use_reparam = layer_idx in tuple(xib_layer_indices)
            self.layers.append(
                ExtendedGIBGATLayer(
                    in_channels=in_ch,
                    out_channels=hidden_channels,
                    heads=heads,
                    concat=True,
                    max_hop=max_hop,
                    k_samples=k_samples,
                    temperature=temperature,
                    bern_prior_alpha=bern_prior_alpha,
                    negative_slope=negative_slope,
                    use_reparam=use_reparam,
                    prior_components=prior_components,
                    val_use_mean=val_use_mean,
                )
            )

        readout_dim = hidden_channels * heads
        self.graph_head = nn.Linear(readout_dim, num_classes)

    def forward(  # type: ignore[override]
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        batch: Optional[torch.Tensor] = None,
        training: Optional[bool] = None,
    ) -> Tuple[torch.Tensor, Dict[str, List[torch.Tensor]], torch.Tensor, torch.Tensor]:
        if training is None:
            training = self.training

        num_nodes = x.shape[0]
        if batch is None:
            batch = torch.zeros(num_nodes, dtype=torch.long, device=x.device)

        hop_pools = build_hop_pools(edge_index, num_nodes, self.max_hop)
        edge_lookup = build_edge_lookup(edge_index)

        reg_info: Dict[str, List[torch.Tensor]] = {
            "ixz_list": [],
            "structure_kl_list": [],
            "edge_kl_list": [],
        }
        edge_kl_layers: List[torch.Tensor] = []

        h = F.dropout(x, p=self.dropout, training=training)
        for layer_idx, layer in enumerate(self.layers):
            h, ixz, structure_kl, edge_kl = layer(
                h, hop_pools, edge_index, edge_attr, edge_lookup, training=training,
            )
            reg_info["ixz_list"].append(ixz)
            reg_info["structure_kl_list"].append(structure_kl)
            reg_info["edge_kl_list"].append(edge_kl)
            edge_kl_layers.append(edge_kl)

            if layer_idx < self.num_layers - 1:
                h = F.elu(h)
                h = F.dropout(h, p=self.dropout, training=training)

        graph_repr = _global_sum_pool(h, batch)
        graph_logits = self.graph_head(graph_repr)

        per_edge_kl = torch.stack(edge_kl_layers, dim=0).sum(dim=0)
        per_node_ixz = self._aggregate_node_ixz(reg_info["ixz_list"])

        return graph_logits, reg_info, per_edge_kl, per_node_ixz

    @staticmethod
    def _aggregate_node_ixz(ixz_list: List[torch.Tensor]) -> torch.Tensor:
        """Sum per-node XIB contributions over layers that emit non-zero IXz."""
        total = torch.zeros_like(ixz_list[0])
        for ixz in ixz_list:
            if ixz.abs().sum() > 0:
                total = total + ixz
        return total


def _global_sum_pool(x: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
    """Sum-pool node features into one vector per graph in ``batch``."""
    num_graphs = int(batch.max().item()) + 1
    out = torch.zeros(num_graphs, x.shape[1], device=x.device, dtype=x.dtype)
    out.scatter_add_(0, batch.unsqueeze(-1).expand_as(x), x)
    return out


def ib_beta_multiplier(epoch: int, max_epochs: int) -> float:
    """IB warm-up / anneal schedule from `design.md` §5.1 (25% / 25–50% / hold)."""
    if max_epochs <= 0:
        return 1.0
    frac = epoch / max_epochs
    if frac < 0.25:
        return 0.0
    if frac < 0.50:
        return (frac - 0.25) / 0.25
    return 1.0
