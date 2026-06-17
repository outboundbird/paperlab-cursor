# gib-importance experiment

Exploratory probe: does GIBGAT's per-element AIB-Bern / XIB KL recover planted
importance on a synthetic graph-classification dataset?

**Design spec:** `vault/experiments/gib-importance/design.md` (PaperLab vault).

**Stage-1 dependency:** GIB-Bern primitives are imported from the GIBGAT vault
reconstruction (not modified by this experiment):

`C:\Users\e0482362\OneDrive - Sanofi\Workspace\Topics\public\Modeling\PaperLab\GIBGAT\code\method.py`

(resolve at runtime via `tools.paths.vault_code_dir("GIBGAT")`).

This build follows the **Stage-2 extension regime** (added 2026-06-16):
single-method experiment, `methods/<slug>/extended.py` inherits/composes the
audited Stage-1 `method.py`, gated by the critic's extension-fidelity mode.

## Layout

```
sandbox/experiments/gib-importance/
├── synth/generate.py          # synthetic dataset (design §6)
├── methods/
│   └── gibgat/
│       ├── _vault_import.py   # importlib loader for vault method.py
│       └── extended.py        # ExtendedGIBGATLayer / ExtendedGIBGAT
│                              #   inherit from Stage-1 GIBGATLayer / Method
├── run/
│   ├── train_and_recover.py   # train, dump KLs, recovery metrics
│   └── results/               # JSON outputs (git-tracked if small)
└── data/                      # generated datasets (git-ignored)
```

## Prerequisites

- Repo `paperlab.config.yaml` configured (`vault_paperlab_path` must resolve).
- Python env with `torch`, `torch_geometric`, `numpy`, `scikit-learn`.

From the repo root:

```bash
cd sandbox/experiments/gib-importance
```

## 1. Generate synthetic data (optional)

The training script regenerates data per seed by default. To materialize archives:

```bash
python -c "
from pathlib import Path
from synth.generate import generate_dataset, save_dataset
out = Path('data/seed_0')
save_dataset(generate_dataset(0), out)
print('saved', out)
"
```

Pinned data seed = `42`; each model seed combines via `numpy.random.SeedSequence`.

## 2. Smoke test (pipeline check)

```bash
python run/train_and_recover.py --smoke
```

Runs 5 epochs on 10 graphs; writes `run/results/smoke_results.json`.

## 3. Full experiment (user-run)

Five seeds `{0,1,2,3,4}`, 2000-epoch cap, early stopping on validation F1-micro:

```bash
python run/train_and_recover.py --max-epochs 2000 --batch-size 16
```

Writes `run/results/results.json` with per-seed and aggregate metrics:

- edge / node recovery AUROC (mean ± std across seeds)
- top-7 precision (planted count)
- graph-classification test accuracy (75% interpretability gate per design H3)
- random-ranking AUROC baseline

## Extensions vs published GIBGAT

1. **Sum-pool readout** + graph-level CE (2 classes).
2. **Edge-feature-aware attention:** `(Z̃_v ⊕ e_{vu} ⊕ Z̃_u) a^T` in the GIB-Bern path.
3. **Telemetry:** per-directed-edge AIB-Bern KL (summed over layers) and per-node XIB KL.

Hyperparameters match design §5.1: `T=1`, `β₁=0.001`, `β₂=0.01`, IB warm-up /
anneal schedule, 8 heads, dropout 0.6, LR 0.01.
