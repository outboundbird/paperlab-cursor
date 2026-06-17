"""Synthetic graph dataset for the gib-importance exploratory probe.

Generative process matches ``design.md`` section 6: 40-node graphs, planted
satellite patterns A/B/C, ground-truth node/edge importance labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import torch
from torch_geometric.data import Data

N_GRAPHS = 200
N_NODES = 40
N_UNDIRECTED_EDGES = 120
N_NODE_FEATURES = 1
N_EDGE_FEATURES = 1
N_PATTERN_A_NODES = 4
N_PATTERN_B_EDGES = 4
N_PATTERN_C_NODES = 3
MU_DEFAULT = 1.0
DATA_SEED = 42
TRAIN_SIZE = 140
VAL_SIZE = 30
TEST_SIZE = 30
SplitName = Literal["train", "val", "test"]


@dataclass
class DatasetSplits:
    """Train / val / test graph lists with stratified class balance."""

    train: List[Data]
    val: List[Data]
    test: List[Data]
    model_seed: int
    combined_seed: int


def combine_seed(data_seed: int, model_seed: int) -> int:
    """Deterministic combined seed for per-model dataset streams."""
    return int(np.random.SeedSequence([data_seed, model_seed]).generate_state(1)[0])


def _canonical_edge(u: int, v: int) -> Tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _sample_remaining_edges(
    rng: np.random.Generator,
    n_nodes: int,
    required: set[Tuple[int, int]],
    target_count: int,
) -> set[Tuple[int, int]]:
    """Sample undirected edges until ``target_count`` unique pairs exist."""
    edges = set(required)
    max_pairs = n_nodes * (n_nodes - 1) // 2
    if target_count > max_pairs:
        raise ValueError(f"Cannot sample {target_count} edges on {n_nodes} nodes.")

    all_pairs = [
        (i, j)
        for i in range(n_nodes)
        for j in range(i + 1, n_nodes)
        if (i, j) not in edges
    ]
    rng.shuffle(all_pairs)
    for pair in all_pairs:
        if len(edges) >= target_count:
            break
        edges.add(pair)
    if len(edges) != target_count:
        raise RuntimeError(
            f"Edge sampling failed: got {len(edges)}, want {target_count}."
        )
    return edges


def _build_directed_edge_index(
    undirected_edges: set[Tuple[int, int]],
) -> Tuple[torch.Tensor, Dict[Tuple[int, int], int]]:
    """COO edge_index with both directions; map directed pair to row index."""
    rows: List[int] = []
    cols: List[int] = []
    directed_to_idx: Dict[Tuple[int, int], int] = {}
    for u, v in sorted(undirected_edges):
        for s, d in ((u, v), (v, u)):
            directed_to_idx[(s, d)] = len(rows)
            rows.append(s)
            cols.append(d)
    edge_index = torch.tensor([rows, cols], dtype=torch.long)
    return edge_index, directed_to_idx


def generate_graph(
    class_label: int,
    rng: np.random.Generator,
    mu: float = MU_DEFAULT,
) -> Data:
    """Generate one attributed graph with planted patterns and importance labels."""
    mu_n = mu
    mu_e = mu

    nodes = np.arange(N_NODES)
    rng.shuffle(nodes)
    nodes_a = nodes[:N_PATTERN_A_NODES]
    nodes_c = nodes[N_PATTERN_A_NODES:N_PATTERN_A_NODES + N_PATTERN_C_NODES]
    pattern_nodes = set(nodes_a) | set(nodes_c)

    # Triangle on pattern-C nodes.
    c_list = list(nodes_c)
    c_undirected = {
        _canonical_edge(c_list[0], c_list[1]),
        _canonical_edge(c_list[1], c_list[2]),
        _canonical_edge(c_list[0], c_list[2]),
    }

    other_nodes = [i for i in range(N_NODES) if i not in pattern_nodes]
    if len(other_nodes) < 2:
        raise RuntimeError("Insufficient non-pattern nodes for pattern B.")

    b_candidates = [
        _canonical_edge(other_nodes[i], other_nodes[j])
        for i in range(len(other_nodes))
        for j in range(i + 1, len(other_nodes))
        if _canonical_edge(other_nodes[i], other_nodes[j]) not in c_undirected
    ]
    rng.shuffle(b_candidates)
    if len(b_candidates) < N_PATTERN_B_EDGES:
        raise RuntimeError("Insufficient candidate edges for pattern B.")
    b_undirected = set(b_candidates[:N_PATTERN_B_EDGES])

    required = c_undirected | b_undirected
    all_undirected = _sample_remaining_edges(
        rng, N_NODES, required, N_UNDIRECTED_EDGES
    )

    edge_index, _ = _build_directed_edge_index(all_undirected)

    x = np.zeros((N_NODES, N_NODE_FEATURES), dtype=np.float32)
    edge_attr = np.zeros((edge_index.shape[1], N_EDGE_FEATURES), dtype=np.float32)
    node_importance = np.zeros(N_NODES, dtype=np.float32)
    edge_importance = np.zeros(edge_index.shape[1], dtype=np.float32)

    sign = 1.0 if class_label == 1 else -1.0

    for node in nodes_a:
        x[node, 0] = rng.normal(sign * mu_n, 1.0)
        node_importance[node] = 1.0

    for node in nodes_c:
        x[node, 0] = rng.normal(sign * mu, 1.0)
        node_importance[node] = 1.0

    for node in range(N_NODES):
        if node_importance[node] == 0.0:
            x[node, 0] = rng.normal(0.0, 1.0)

    b_sign = -sign  # pattern B edge sign inverted relative to pattern A
    for u, v in all_undirected:
        cu, cv = _canonical_edge(u, v)
        is_b = (cu, cv) in b_undirected
        is_c = (cu, cv) in c_undirected
        if is_b:
            feat = rng.normal(b_sign * mu_e, 1.0)
        elif is_c:
            feat = rng.normal(sign * mu, 1.0)
        else:
            feat = rng.normal(0.0, 1.0)

        for s, d in ((u, v), (v, u)):
            idx = next(
                i
                for i in range(edge_index.shape[1])
                if edge_index[0, i] == s and edge_index[1, i] == d
            )
            edge_attr[idx, 0] = feat
            if is_b or is_c:
                edge_importance[idx] = 1.0

    data = Data(
        x=torch.from_numpy(x),
        edge_index=edge_index,
        edge_attr=torch.from_numpy(edge_attr),
        y=torch.tensor([class_label], dtype=torch.long),
    )
    data.node_importance = torch.from_numpy(node_importance)
    data.edge_importance = torch.from_numpy(edge_importance)
    data.nodes_a = torch.tensor(nodes_a, dtype=torch.long)
    data.nodes_c = torch.tensor(nodes_c, dtype=torch.long)
    return data


def generate_dataset(
    model_seed: int,
    data_seed: int = DATA_SEED,
    mu: float = MU_DEFAULT,
) -> DatasetSplits:
    """Build 200 graphs with stratified 140/30/30 splits."""
    combined = combine_seed(data_seed, model_seed)
    rng = np.random.default_rng(combined)

    graphs: List[Data] = []
    for label in (0, 1):
        for _ in range(N_GRAPHS // 2):
            graphs.append(generate_graph(label, rng, mu=mu))

    rng.shuffle(graphs)

    train: List[Data] = []
    val: List[Data] = []
    test: List[Data] = []
    n_train_per_class = TRAIN_SIZE // 2
    n_val_per_class = VAL_SIZE // 2
    n_test_per_class = TEST_SIZE // 2

    for label in (0, 1):
        class_graphs = [g for g in graphs if int(g.y.item()) == label]
        train.extend(class_graphs[:n_train_per_class])
        val.extend(
            class_graphs[n_train_per_class:n_train_per_class + n_val_per_class]
        )
        test.extend(
            class_graphs[
                n_train_per_class + n_val_per_class:n_train_per_class + n_val_per_class + n_test_per_class
            ]
        )

    return DatasetSplits(
        train=train,
        val=val,
        test=test,
        model_seed=model_seed,
        combined_seed=combined,
    )


def save_dataset(splits: DatasetSplits, out_dir: Path) -> None:
    """Persist splits as ``torch`` archives (git-ignored ``data/`` convention)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "train": splits.train,
            "val": splits.val,
            "test": splits.test,
            "model_seed": splits.model_seed,
            "combined_seed": splits.combined_seed,
        },
        out_dir / "dataset.pt",
    )


def load_dataset(data_dir: Path) -> DatasetSplits:
    """Load a dataset archive written by ``save_dataset``."""
    payload = torch.load(data_dir / "dataset.pt", weights_only=False)
    return DatasetSplits(
        train=payload["train"],
        val=payload["val"],
        test=payload["test"],
        model_seed=int(payload["model_seed"]),
        combined_seed=int(payload["combined_seed"]),
    )


if __name__ == "__main__":
    splits = generate_dataset(model_seed=0)
    print(
        f"train={len(splits.train)} val={len(splits.val)} test={len(splits.test)} "
        f"combined_seed={splits.combined_seed}"
    )
    g = splits.train[0]
    print(
        f"sample: nodes={g.x.shape[0]} edges={g.edge_index.shape[1]} "
        f"important_nodes={int(g.node_importance.sum())} "
        f"important_edges={int(g.edge_importance.sum())}"
    )
