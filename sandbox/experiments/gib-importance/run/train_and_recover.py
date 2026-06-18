"""Train extended GIBGAT and compute importance-recovery metrics."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import f1_score, roc_auc_score
from torch_geometric.data import Batch

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXP_DIR))

from methods.gibgat.extended import ExtendedGIBGAT, ib_beta_multiplier
from methods.gibgat._vault_import import gibgat_method_path
from synth.generate import (
    DATA_SEED,
    MU_DEFAULT,
    N_GRAPHS,
    generate_dataset,
    save_dataset,
)

DEFAULT_SEEDS = [0, 1, 2, 3, 4]
BETA_1 = 0.001
BETA_2 = 0.01
MAX_EPOCHS = 2000
LR = 0.01
ACCURACY_GATE = 0.75
AUROC_COMMIT = 0.75
TOP_K = 7
EARLY_STOP_PATIENCE = 50


@dataclass
class TrainConfig:
    max_epochs: int = MAX_EPOCHS
    batch_size: int = 16
    lr: float = LR
    beta_1: float = BETA_1
    beta_2: float = BETA_2
    seeds: Sequence[int] = field(default_factory=lambda: list(DEFAULT_SEEDS))
    smoke: bool = False


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)


def collate_graphs(graphs: List) -> Batch:
    return Batch.from_data_list(graphs)


def compute_loss(
    model: ExtendedGIBGAT,
    batch: Batch,
    beta_mult: float,
    beta_1: float,
    beta_2: float,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    logits, reg_info, _, ixz_nodes = model(
        batch.x,
        batch.edge_index,
        batch.edge_attr,
        batch=batch.batch,
        training=True,
    )
    ce = F.cross_entropy(logits, batch.y)

    # design.md §5.1: AIB/XIB are summed over nodes/edges within each graph
    # and averaged across the batch. structure_kl_list[l] is already a
    # batch-wide sum of per-candidate Bernoulli KLs, and ixz_list[l] is
    # per-node IXz over the collated node tensor; both are reduced to a
    # per-graph mean by dividing the batch sum by num_graphs.
    num_graphs = int(batch.num_graphs)

    aib = sum(reg_info["structure_kl_list"]) / num_graphs
    xib_layers = [
        ixz.sum() / num_graphs
        for ixz in reg_info["ixz_list"]
        if ixz.abs().sum() > 0
    ]
    xib = sum(xib_layers) if xib_layers else torch.zeros((), device=logits.device)

    loss = ce + beta_mult * beta_1 * aib + beta_mult * beta_2 * xib
    return loss, {
        "ce": float(ce.detach()),
        "aib": float(aib.detach()),
        "xib": float(xib.detach()),
        "total": float(loss.detach()),
    }


def train_one_seed(
    model_seed: int,
    config: TrainConfig,
    data_dir: Optional[Path] = None,
) -> Dict:
    set_seed(model_seed)

    if config.smoke:
        splits = generate_dataset(model_seed=0, data_seed=DATA_SEED, mu=MU_DEFAULT)
        splits.train = splits.train[:5]
        splits.val = splits.val[:2]
        splits.test = splits.test[:2]
        max_epochs = 5
        patience = 5
    else:
        splits = generate_dataset(model_seed=model_seed, data_seed=DATA_SEED, mu=MU_DEFAULT)
        max_epochs = config.max_epochs
        patience = EARLY_STOP_PATIENCE
        if data_dir is not None:
            save_dataset(splits, data_dir / f"seed_{model_seed}")

    model = ExtendedGIBGAT(
        in_channels=1,
        num_classes=2,
        hidden_channels=8,
        heads=8,
        num_layers=2,
        max_hop=1,
        dropout=0.6,
        xib_layer_indices=(0,),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr)

    best_val_f1 = -1.0
    best_state: Optional[Dict[str, torch.Tensor]] = None
    stale_epochs = 0

    train_graphs = splits.train
    val_graphs = splits.val

    for epoch in range(max_epochs):
        model.train()
        beta_mult = ib_beta_multiplier(epoch, max_epochs)
        perm = np.random.permutation(len(train_graphs))
        epoch_loss = 0.0
        for start in range(0, len(train_graphs), config.batch_size):
            idx = perm[start:start + config.batch_size]
            batch = collate_graphs([train_graphs[i] for i in idx])
            optimizer.zero_grad()
            loss, _ = compute_loss(model, batch, beta_mult, config.beta_1, config.beta_2)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        model.eval()
        val_preds: List[int] = []
        val_labels: List[int] = []
        with torch.no_grad():
            for start in range(0, len(val_graphs), config.batch_size):
                batch = collate_graphs(val_graphs[start:start + config.batch_size])
                logits, _, _, _ = model(
                    batch.x,
                    batch.edge_index,
                    batch.edge_attr,
                    batch=batch.batch,
                    training=False,
                )
                val_preds.extend(logits.argmax(dim=-1).cpu().tolist())
                val_labels.extend(batch.y.cpu().tolist())

        val_f1 = f1_score(val_labels, val_preds, average="micro", zero_division=0)
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    metrics = evaluate_recovery(model, splits.test, model_seed)
    metrics["model_seed"] = model_seed
    metrics["best_val_f1_micro"] = best_val_f1
    metrics["epochs_run"] = epoch + 1
    return metrics


def _collapse_undirected_edges(
    edge_index: torch.Tensor,
    scores: np.ndarray,
    labels: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Average directed scores/labels into canonical undirected pairs."""
    pair_scores: Dict[Tuple[int, int], List[float]] = {}
    pair_labels: Dict[Tuple[int, int], List[float]] = {}
    for i in range(edge_index.shape[1]):
        u = int(edge_index[0, i])
        v = int(edge_index[1, i])
        key = (u, v) if u < v else (v, u)
        pair_scores.setdefault(key, []).append(float(scores[i]))
        pair_labels.setdefault(key, []).append(float(labels[i]))

    collapsed_scores = np.array([np.mean(pair_scores[k]) for k in sorted(pair_scores)])
    collapsed_labels = np.array([max(pair_labels[k]) for k in sorted(pair_labels)])
    return collapsed_scores, collapsed_labels


def evaluate_recovery(
    model: ExtendedGIBGAT,
    test_graphs: List,
    model_seed: int,
) -> Dict:
    model.eval()
    edge_aurocs: List[float] = []
    node_aurocs: List[float] = []
    edge_topk: List[float] = []
    node_topk: List[float] = []
    random_edge_aurocs: List[float] = []
    random_node_aurocs: List[float] = []
    correct = 0
    total = 0

    rng = np.random.default_rng(model_seed)

    with torch.no_grad():
        for graph in test_graphs:
            logits, _, per_edge_kl, per_node_ixz = model(
                graph.x,
                graph.edge_index,
                graph.edge_attr,
                training=False,
            )
            pred = int(logits.argmax(dim=-1).item())
            label = int(graph.y.item())
            correct += int(pred == label)
            total += 1

            edge_scores = per_edge_kl.cpu().numpy()
            edge_gt = graph.edge_importance.cpu().numpy()
            edge_scores_u, edge_gt_u = _collapse_undirected_edges(
                graph.edge_index, edge_scores, edge_gt
            )
            node_scores = per_node_ixz.cpu().numpy()
            node_gt = graph.node_importance.cpu().numpy()

            if edge_gt_u.max() > edge_gt_u.min():
                edge_aurocs.append(float(roc_auc_score(edge_gt_u, edge_scores_u)))
                random_edge_aurocs.append(
                    float(roc_auc_score(edge_gt_u, rng.random(edge_gt_u.shape)))
                )
            edge_topk.append(_top_k_precision(edge_scores_u, edge_gt_u, TOP_K))

            if node_gt.max() > node_gt.min():
                node_aurocs.append(float(roc_auc_score(node_gt, node_scores)))
                random_node_aurocs.append(
                    float(roc_auc_score(node_gt, rng.random(node_gt.shape)))
                )
            node_topk.append(_top_k_precision(node_scores, node_gt, TOP_K))

    accuracy = correct / max(total, 1)
    result = {
        "test_accuracy": accuracy,
        "accuracy_gate_passed": accuracy >= ACCURACY_GATE,
        "edge_auroc_mean": _mean_std(edge_aurocs),
        "node_auroc_mean": _mean_std(node_aurocs),
        "edge_top7_precision_mean": _mean_std(edge_topk),
        "node_top7_precision_mean": _mean_std(node_topk),
        "random_edge_auroc_mean": _mean_std(random_edge_aurocs),
        "random_node_auroc_mean": _mean_std(random_node_aurocs),
        "recovery_interpretable": accuracy >= ACCURACY_GATE,
    }
    return result


def _top_k_precision(scores: np.ndarray, labels: np.ndarray, k: int) -> float:
    k = min(k, scores.shape[0])
    top_idx = np.argsort(-scores)[:k]
    return float(labels[top_idx].sum() / k)


def _mean_std(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": math.nan, "std": math.nan, "n": 0}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=0)),
        "n": len(values),
    }


def aggregate_seed_results(per_seed: List[Dict]) -> Dict:
    def agg_metric(key: str) -> Dict[str, float]:
        means = [s[key]["mean"] for s in per_seed if not math.isnan(s[key]["mean"])]
        return _mean_std(means)

    accuracies = [float(s["test_accuracy"]) for s in per_seed]

    return {
        "edge_auroc": agg_metric("edge_auroc_mean"),
        "node_auroc": agg_metric("node_auroc_mean"),
        "edge_top7_precision": agg_metric("edge_top7_precision_mean"),
        "node_top7_precision": agg_metric("node_top7_precision_mean"),
        "test_accuracy": _mean_std(accuracies),
        "random_edge_auroc": agg_metric("random_edge_auroc_mean"),
        "random_node_auroc": agg_metric("random_node_auroc_mean"),
    }


def run_experiment(config: TrainConfig) -> Dict:
    per_seed = []
    data_dir = EXP_DIR / "data" if not config.smoke else None

    for seed in config.seeds:
        if config.smoke:
            per_seed.append(train_one_seed(0, config, data_dir))
            break
        per_seed.append(train_one_seed(seed, config, data_dir))

    aggregate = aggregate_seed_results(per_seed)
    return {
        "topic": "gib-importance",
        "design_source": "vault/experiments/gib-importance/design.md",
        "gibgat_method_path": str(gibgat_method_path()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "max_epochs": config.max_epochs if not config.smoke else 5,
            "beta_1": config.beta_1,
            "beta_2": config.beta_2,
            "lr": config.lr,
            "seeds": list(config.seeds) if not config.smoke else [0],
            "smoke": config.smoke,
            "data_seed": DATA_SEED,
            "mu": MU_DEFAULT,
            "n_graphs": N_GRAPHS if not config.smoke else 10,
        },
        "hypothesis_thresholds": {
            "auroc": AUROC_COMMIT,
            "accuracy_gate": ACCURACY_GATE,
        },
        "per_seed": per_seed,
        "aggregate": aggregate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train extended GIBGAT and evaluate recovery.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Smoke run for the coder smoke gate (`ml-experiment-code` "
            "§ STAGE 2 — Smoke gate): one seed, smallest dataset, "
            "5 epochs. Scratch output goes to `results/.smoke/` and is "
            "removed before exit. Exit 0 on success, non-zero on any "
            "unhandled exception."
        ),
    )
    parser.add_argument("--max-epochs", type=int, default=MAX_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seeds", type=int, nargs="*", default=DEFAULT_SEEDS)
    args = parser.parse_args()

    config = TrainConfig(
        max_epochs=args.max_epochs,
        batch_size=args.batch_size,
        seeds=args.seeds,
        smoke=args.smoke,
    )

    results = run_experiment(config)
    base_results_dir = EXP_DIR / "run" / "results"
    if config.smoke:
        out_dir = base_results_dir / ".smoke"
    else:
        out_dir = base_results_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ("smoke_results.json" if config.smoke else "results.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Wrote {out_path}")
    if config.smoke:
        acc = results["per_seed"][0]["test_accuracy"]
        print(f"smoke test_accuracy={acc:.3f}")
        # Spec compliance: smoke must not pollute results/ proper.
        # The .smoke/ scratch folder is removed before exit so the
        # evaluator never picks up smoke output as a real run result.
        shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
