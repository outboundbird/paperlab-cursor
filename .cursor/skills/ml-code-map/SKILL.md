# ML Code Map Schema

## Purpose

This file defines the schema for code_map.md, the structured mapping from a paper's algorithm to its official implementation. code_map.md is produced by the @implementer agent and read by the user to understand how the paper translates to code. It lives at papers/<slug>/code_map.md.

## Conventions

Global rules that apply to all sections:
- **audience**: Audience: reader who has already read spec.md and is fluent in Python + the paper's primary framework (PyTorch, JAX, etc.). Assume familiarity with common ML idioms (nn.Module, forward methods, message-passing); do not re-explain these.
- **invocation**: Invocation: per-paper. Implementer processes one paper's full repo at a time and produces one code_map.md.
- **length**: 1 - 8 pages
- **code snippet max length**:  20 lines
- **code block**: Code blocks must be verbatim except for inline clarifying comments that tie variables to paper notation. If Implementer adds a comment, mark it as Implementer-added (e.g., a trailing # [annot]).
- **language tag convention**: based on the original code
- **commit/date recording convention**: MM/DD/YYYY
- **the "read-only" boundary**: Read-only boundary: Implementer uses only Read, Glob, and Grep. It does not execute code (no Bash), does not modify upstream/ files, and does not produce new Python files. Its only writes are to papers/<slug>/code_map.md.
- **accuracy rule for line numbers**: Line numbers must reflect actual file contents at the annotated commit. Verify each line range by reading the file — do not infer line numbers from imports, class names, or file structure. Inline code snippets must exactly match the file content at those line ranges.
- **what triggers re-annotation**: If the upstream repository has been updated since the commit recorded in the header, line numbers and code snippets may have drifted. Re-run Implementer to refresh code_map.md after any upstream update.


## Required sections

### 1. Header

Every code_map.md must begins with a document header in this format:

```markdown
---
category: model
tags:
- claude-guided-paper-reading
- code-map
---

# Code Mapping — <slug>

## 1. Annotation Info

**Paper:** <paper title>
**Paper context:** one-sentence summary of what the paper does
**Repo:** `upstream/<slug>/<repo-subdir>/`, source URL (<URL>),
**Annotation date:** MM/DD/YYYY. No commit hash required — Implementer records the date it read the repo. If the upstream updates, re-run to refresh
**Code language/framework:** <e.g., Python + PyTorch + PyTorch Geometric>

---
```

Example (filled in for GEARS):

```markdown
---
category: model
tags:
- claude-guided-paper-reading
- code-map
---

# Code Mapping — GEARS

## 1. Annotation Info

**Paper:** Predicting transcriptional outcomes of novel multigene
perturbations with GEARS
**Paper context:** GNN + GO-graph method for predicting transcriptional
response to unseen gene perturbations.
**Repo:** `upstream/GEARS/GEARS/`, https://github.com/snap-stanford/GEARS,
annotation date: 04/23/2026
**Code language/framework:** Python + PyTorch + PyTorch Geometric

---
```

Use the annotation date (MM/DD/YYYY) rather than a commit hash — simpler to capture without running git commands, good enough for freshness tracking.

### 2. Per-algorithm-component mapping (the main content)

In this section you will provide the section code that maps to the major paper algorithm components.
Specifically you will write up:

- Provide the brief section title
- Cite the paper formula from spec.md correspond to this section if available
- Provide the code location with information of code path: `upstream/<slug>/<git repo>/<code file>` : lines xx -xx
- The snippet of the that corresponding to the algorithm
- **code snippet max length**:  20 lines
- Annotation for this piece of code.
- If a component spans multiple files (e.g., the model is in model.py but its loss is in losses.py), include multiple Code location + code block pairs within the same component subsection. Do not split one component across multiple subsections.

for example:

**Gene co-expression graph encoder**

**Paper formula** (from `spec.md §6`):

$$\mathbf{h}^{\text{gene}}_u = \text{GNN}_{\theta_g}(\mathbf{x}^{\text{gene}}_u, \mathcal{G}_{\text{gene}}) \in \mathbb{R}^d$$

**Code location:** `upstream/GEARS/gears/model.py` lines 48–72

```python
class PertGeneEncoder(nn.Module):
    def __init__(self, num_genes, hidden_size, ...):
        super().__init__()
        self.gene_emb = nn.Embedding(num_genes, hidden_size)
        self.gnn = SimpleConv(hidden_size, hidden_size)
        # ... (abbreviated)

    def forward(self, x, edge_index):
        h = self.gene_emb(x)         # x^gene_u — learnable gene embedding
        h = self.gnn(h, edge_index)  # message passing on G_gene
        return h                     # h^gene_u ∈ R^d
```

**Annotation:**
- `self.gene_emb(x)` produces $\mathbf{x}^{\text{gene}}_u$ — the learnable
  per-gene embedding. Paper notation; code variable is `h` after this line.
- `self.gnn` is a single-layer SGC (Simplifying Graph Convolution) as
  specified in `spec.md §7` (`GNN layers = 1`, `GNN architecture = SGC`).
  The `edge_index` argument is $\mathcal{G}_{\text{gene}}$, computed once
  at preprocessing time (see `upstream/GEARS/gears/data_utils.py:L112`).
- The output `h` is $\mathbf{h}^{\text{gene}}_u \in \mathbb{R}^d$,
  ready to be combined with the perturbation embedding $\mathbf{h}^z$
  in the next module.


### 3. Training loop structure (numbered list)

Write a numbered list that describes the training loop structure. Briefly summarize each step. Each step is concrete, each step points at a specific file and ideally line range, and the sequence corresponds to the paper's algorithm description. That way the reader can go from "spec.md §6.1 step 2 says X" to "code step 3 does X" without guessing.

For example:

1. Entry point: `python -m gears.train --config configs/gears_norman.yaml`
   → `upstream/GEARS/gears/train.py:L1-30`. Parses CLI args, loads config.
2. Data loading: `gears/data.py:PertData` class loads LINCS-formatted
   perturbation data, constructs gene co-expression graph G_gene
   (`data.py:L120-140`) and GO-derived perturbation graph G_pert
   (`data.py:L180-210`).
3. Model initialization: `gears/model.py:GEARSModel` constructs the two
   GNN encoders (gene + pert) and the cross-gene MLP decoder
   (`model.py:L40-90`).
4. Training loop: `gears/trainer.py:train()` runs epochs. Each iteration
   batches cells, computes forward pass through both GNNs (corresponding
   to spec.md §6.1 steps 3-5), computes autofocus + direction losses
   (`trainer.py:L130-160`), and updates parameters via Adam.
5. Checkpointing: Every validation improvement saves model weights to
   `checkpoints/<run_name>/`.
6. Inference: Separate entry point `python -m gears.predict`
   (`gears/predict.py`) loads trained weights and predicts post-perturbation
   expression for novel perturbation sets.



### 4. Configuration layer (table)

Provide a markdown table that specify the layers used in the deep learning model if available.
If the model does not concern deep learning model, leave 'Not applicable'.

For example:

| Hyperparameter (from spec.md §7) | Code location | Default | How to override |
|---|---|---|---|
| Hidden embedding dimension $d$ | `gears/model.py:L22` | 64 | `--hidden_size` CLI arg or `hidden_size` in YAML config |
| Autofocus loss exponent $\gamma$ | `gears/trainer.py:L88` | 2 | `--gamma` CLI arg |
| Direction loss weight $\lambda$ | `gears/trainer.py:L90` | 0.1 | `--direction_lambda` CLI arg |
| Number of GNN layers | `gears/model.py:L45` | 1 (SGC) | `configs/*.yaml` under `model.n_layers` |
| Learning rate | `gears/trainer.py:L62` | 1e-3 | `--lr` CLI arg |
| Batch size | `gears/data.py:L250` | 32 | `--batch_size` CLI arg |

### 5. Gotchas (bulleted list with paper-says / code-does / why-it-matters)

Provide a list that the code is inconsistent with what paper stated. Provide the reason why it is importance to know this difference.

Only include genuine gotchas — discrepancies that would mislead a reader or affect reproduction. Do not include: different variable names, different formatting, different organization, or non-functional stylistic differences. If in doubt about whether something qualifies, omit it.

For example:

- **Paper says:** $\mathbf{h}^{\text{post-pert}}_u = \text{MLP}(\mathbf{h}^{\text{gene}}_u + \mathbf{h}^z)$ (addition)
- **Code does:** `torch.cat([h_gene, h_z], dim=-1)` followed by an MLP
  that halves the dimension (`gears/model.py:L89`)
- **Why it matters:** Concatenation + MLP is strictly more expressive
  than addition — the paper's formula is a simplification. The learned
  MLP could recover addition as a special case, but nothing forces it to.

### 6. Cross-references

A short list of links that help the reader navigate between code_map.md
and the paper's other artifacts.

**Paper artifacts:**
- [spec.md](spec.md) — the structured extraction of the paper this code
  implements
- [graph-mutilation.md](graph-mutilation.md),
  [causal-markov-condition.md](causal-markov-condition.md), etc. —
  individual concept explanations (list whichever exist for this paper)

**Upstream repository:**
- Official source: <URL>
- Local clone: `upstream/<slug>/`

**External references** (optional):
- Any documentation, tutorials, or blog posts from the authors that help
  with the code specifically (not about the method; that's spec.md's job)

Include only links that genuinely help. If no per-concept explanation
files exist yet, list only spec.md under "Paper artifacts."