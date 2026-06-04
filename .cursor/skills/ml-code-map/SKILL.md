---
name: ml-code-map
description: Maps an ML paper's algorithmic concepts to a concrete implementation and defines the `code_map.md` schema. The implementation is either the cloned official code under `repo_upstream_dir(slug)` (official source) OR the coder's reconstructed Stage-1 code under `vault_code_dir(slug)` (reconstructed source). Writes `code_map.md` to `vault_path(slug, "code_map.md")` (in the vault). Use when mapping, annotating, or explaining a paper's code — official or reconstructed.
---

# ML Code Map Schema

## Purpose

This file defines the schema for `code_map.md`, the structured mapping from a paper's algorithm to a concrete implementation. `code_map.md` is produced by the Implementer subagent and read by the user to understand how the paper translates to code. It lives at `vault_path(slug, "code_map.md")` (resolved via `tools/paths.py`).

## Two sources, one schema

`code_map.md` maps one of two implementations of the same paper. The
schema is identical; only the **source** differs:

| Source | Code location | When | §1 "Source" value |
|---|---|---|---|
| **Official** | `repo_upstream_dir(slug)` | the paper shipped code | `official` |
| **Reconstructed** | `vault_code_dir(slug)` | no official code; the `coder` built it from `code_blueprint.md` (Stage 1) | `reconstructed` |

The implementer determines the source before mapping (see `implementer.md`).
Every reference below to "the code" / "the repo" means **whichever source
applies**. Differences between the two cases are called out inline; where
nothing is said, the rule is identical.

**Reconstructed-source firewall.** When mapping reconstructed code, build
the walkthrough from `spec.md` + the vault `method.py` — **not** from the
`code_blueprint.md` the same implementer may have authored. The map must
re-derive the algorithm↔code correspondence from the paper, so it stays
an independent check rather than a restatement of the blueprint. (The
critic's audit is the firewalled second check; see `ml-critique`.)

## Reading the PDF

When this skill needs paper text (e.g., to cross-reference equations or
algorithm steps against code), extract it via `tools.pdf.extract_pdf_text`,
which uses `pypdf` with a `pdftotext` fallback and caches to
`papers/<slug>/.cache/paper.txt`. Do **not** invent ad-hoc extraction.

```python
from tools.pdf import extract_pdf_text
text = extract_pdf_text(slug)
```

```bash
python -m tools.pdf extract <slug> [--refresh]
```

## Conventions

Global rules that apply to all sections:
- **audience**: Audience: reader who has already read spec.md and is fluent in Python + the paper's primary framework (PyTorch, JAX, etc.). Assume familiarity with common ML idioms (nn.Module, forward methods, message-passing); do not re-explain these.
- **invocation**: Invocation: per-paper. Implementer processes one paper's full repo at a time and produces one code_map.md.
- **length**: 1 - 8 pages
- **code snippet max length**:  20 lines
- **code block**: Code blocks must be verbatim except for inline clarifying comments that tie variables to paper notation. If Implementer adds a comment, mark it as Implementer-added (e.g., a trailing # [annot]).
- **language tag convention**: based on the original code
- **commit/date recording convention**: MM/DD/YYYY
- **the read-only boundary**: The Implementer subagent reads and searches the source files (under `repo_upstream_dir(slug)` for `official`, or `vault_code_dir(slug)` for `reconstructed`), but does not execute the code, modify files there, or produce new Python files. Its only writes are PaperLab annotation artifacts such as `vault_path(slug, "code_map.md")`. (For `reconstructed`, the `method.py` it maps is the `coder`'s — the implementer never edits it.)
- **accuracy rule for line numbers**: Line numbers must reflect actual file contents as read. Verify each line range by reading the file — do not infer line numbers from imports, class names, or file structure. Inline code snippets must exactly match the file content at those line ranges.
- **what triggers re-annotation**: If the source has been updated since the annotation date (the official repo was re-pulled, or the `coder` regenerated the reconstructed `method.py`), line numbers and code snippets may have drifted. Re-run Implementer to refresh code_map.md after any source update.


## Required sections

### 1. Header

Every code_map.md must begins with a document header in this format:

```markdown
---
paper: <slug>
category: model
agent: implementer
status: implemented
sources:
- "[[<slug>/spec.md]]"
concepts:
- "[[<canonical-concept-name>]]"
tags:
- AI-guided-paper-reading
- code-map
---

# Code Mapping — <slug>

## 1. Annotation Info

**Paper:** <paper title>
**Paper context:** one-sentence summary of what the paper does
**Source:** `official` or `reconstructed` (see "Two sources, one schema")
**Code location:** for `official` — absolute path from `repo_upstream_dir(slug)` + source URL (<URL>); for `reconstructed` — absolute path from `vault_code_dir(slug)` (the `coder`'s Stage-1 output)
**Annotation date:** MM/DD/YYYY. No commit hash required — Implementer records the date it read the code. If the source updates, re-run to refresh
**Code language/framework:** <e.g., Python + PyTorch + PyTorch Geometric>

---
```

For a `reconstructed` source, add the disclaimer line directly under the
`# Code Mapping — <slug>` heading:

```markdown
> **Maps reconstructed code** (the `coder`'s Stage-1 output from
> `code_blueprint.md`), **not the authors' official implementation** — no
> upstream repository exists. Mapped against `spec.md` as an independent
> code↔algorithm check.
```

Example (filled in for GEARS):

```markdown
---
paper: GEARS
category: model
agent: implementer
status: implemented
sources:
- "[[GEARS/spec.md]]"
concepts:
- "[[gene-perturbation]]"
tags:
- AI-guided-paper-reading
- code-map
---

# Code Mapping — GEARS

## 1. Annotation Info

**Paper:** Predicting transcriptional outcomes of novel multigene
perturbations with GEARS
**Paper context:** GNN + GO-graph method for predicting transcriptional
response to unseen gene perturbations.
**Source:** `official`
**Code location:** `C:/Users/<you>/Workspace/paperlab-cursor/papers/GEARS/upstream/GEARS/` (i.e. `repo_upstream_dir("GEARS")`), https://github.com/snap-stanford/GEARS
**Annotation date:** 04/23/2026
**Code language/framework:** Python + PyTorch + PyTorch Geometric

---
```

Use the annotation date (MM/DD/YYYY) rather than a commit hash — simpler to capture without running git commands, good enough for freshness tracking.

### 2. Per-algorithm-component mapping (the main content)

In this section you will provide the section code that maps to the major paper algorithm components.
Specifically you will write up:

- Provide the brief section title
- Cite the paper formula from spec.md correspond to this section if available
- Provide the code location as a path relative to the **source root** (`repo_upstream_dir(slug)` for `official`, `vault_code_dir(slug)` for `reconstructed`) followed by line numbers: `<relative path>:lines xx-xx`. The reader resolves the absolute path via `tools/paths.py`. For reconstructed code the path is typically `method.py:lines xx-xx`.
- The snippet of the that corresponding to the algorithm
- **code snippet max length**:  20 lines
- Annotation for this piece of code.
- If a component spans multiple files (e.g., the model is in model.py but its loss is in losses.py), include multiple Code location + code block pairs within the same component subsection. Do not split one component across multiple subsections.

for example:

**Gene co-expression graph encoder**

**Paper formula** (from `spec.md §6`):

$$\mathbf{h}^{\text{gene}}_u = \text{GNN}_{\theta_g}(\mathbf{x}^{\text{gene}}_u, \mathcal{G}_{\text{gene}}) \in \mathbb{R}^d$$

**Code location:** `gears/model.py:lines 48–72` (relative to `repo_upstream_dir("GEARS")`)

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
  at preprocessing time (see `gears/data_utils.py:L112`).
- The output `h` is $\mathbf{h}^{\text{gene}}_u \in \mathbb{R}^d$,
  ready to be combined with the perturbation embedding $\mathbf{h}^z$
  in the next module.


### 3. Training loop structure (numbered list)

Write a numbered list that describes the training loop structure. Briefly summarize each step. Each step is concrete, each step points at a specific file and ideally line range, and the sequence corresponds to the paper's algorithm description. That way the reader can go from "spec.md §6.1 step 2 says X" to "code step 3 does X" without guessing.

For example:

1. Entry point: `python -m gears.train --config configs/gears_norman.yaml`
   → `gears/train.py:L1-30` (under `repo_upstream_dir("GEARS")`). Parses CLI args, loads config.
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

For `reconstructed` source, "How to override" points at the `Method`
constructor keyword argument (from blueprint §2 / `method.py.__init__`)
rather than a CLI flag or YAML key, since reconstructed code has no config
layer.

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

List places where the code is inconsistent with what the paper stated, and why the difference matters.

**The framing depends on the source:**

- **`official`** — a gotcha is an **author choice**: the authors
  implemented something differently from the paper's formula. The
  "why it matters" weighs whether the code or the paper is the better
  reference.
- **`reconstructed`** — there is no third-party author; the `coder` built
  the code from the paper (via the blueprint). A gotcha here is a
  **fidelity finding**: a place where the reconstruction *drifts from the
  paper* (an approximation, a pinned `⚠️ UNCERTAIN` quantity, a
  simplification the blueprint introduced). Frame "why it matters" around
  reconstruction fidelity, not author intent. Use **paper-says /
  code-does / fidelity-note** instead of why-it-matters. If the
  reconstruction is faithful with no drift, say so explicitly ("No
  fidelity gaps found; the reconstruction follows the paper's math.") —
  do not invent gotchas.

Only include genuine gotchas — differences that would mislead a reader or affect reproduction. Do not include: different variable names, formatting, organization, or non-functional stylistic differences. If in doubt, omit it.

For example (`official` source):

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
- Local clone: absolute path from `repo_upstream_dir(slug)`

**External references** (optional):
- Any documentation, tutorials, or blog posts from the authors that help
  with the code specifically (not about the method; that's spec.md's job)

Include only links that genuinely help. If no per-concept explanation
files exist yet, list only spec.md under "Paper artifacts."