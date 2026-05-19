# ML Code Map Deep Dive Mode Schema
This file is a companion schema used by `.cursor/skills/ml-code-map/SKILL.md` and the Implementer subagent for deep-dive mode.

## Purpose

This file defines the schema for deep-dive code mapping. In deep-dive mode, the Implementer subagent produces `vault_path(slug, "code_map__<slug>__<component>.md")` (resolved via `tools/paths.py`).

## Required sections

### 1. Header
The `code_map__<slug>__<component>.md` document begins with header:

```markdown
---
paper: <slug>
paper: <slug>
category: model
tags:
- AI-guided-paper-reading
- code-map-concept
---

# <slug>: <component>

## 1. Annotation Info

**Paper:** <paper title>
**Repo:** absolute path from `repo_upstream_dir(slug)`, source URL (<URL>),
**Annotation date:** MM/DD/YYYY. No commit hash required — Implementer records the date it read the repo. If the upstream updates, re-run to refresh
**Module name**: name of the module code or the component that user asked for
**Code language/framework:** <e.g., Python + PyTorch + PyTorch Geometric>

---
```
for example:

```markdown
---
paper: GEARS
paper: GEARS
category: model
tags:
- AI-guided-paper-reading
- code-map-concept
---

# GEARS: gene-encoder

## 1. Annotation Info

**Paper:** Predicting transcriptional outcomes of novel multigene
perturbations with GEARS
**Repo:** `C:/Users/<you>/Workspace/paperlab-cursor/papers/GEARS/upstream/GEARS/` (i.e. `repo_upstream_dir("GEARS")`), https://github.com/snap-stanford/GEARS,
**Annotation date:**: 04/23/2026
**Module name:** gene encoder
**Code language/framework:** Python + PyTorch + PyTorch Geometric

---
```

### 2. Component

In this section you will provide:

- Fuller code context — up to ~50 lines, including helper functions the component calls.
- Math notation conventions follow `.cursor/skills/ml-code-map/SKILL.md`.
- Tensor-shape walkthrough — for forward() methods, annotate each line with the tensor shape after execution (e.g., `# h: (batch, n_genes, d)`)
- Edge cases — how the code handles special conditions (empty sets, NaN inputs, single-item batches). If none found, state "No explicit edge case handling in this component."

**Example:**

**Code context** (`gears/model.py:lines 48–92`, relative to `repo_upstream_dir("GEARS")`):

```python
class PertGeneEncoder(nn.Module):
    def __init__(self, num_genes, hidden_size, num_layers, ...):
        super().__init__()
        self.gene_emb = nn.Embedding(num_genes, hidden_size)
        self.gnn = SimpleConv(hidden_size, hidden_size)
        self.num_layers = num_layers
        self.dropout = nn.Dropout(0.1)

    def forward(self, x, edge_index):
        # x: (batch, n_genes) — gene indices per cell
        h = self.gene_emb(x)              # h: (batch, n_genes, hidden_size)
        for _ in range(self.num_layers):
            h = self.gnn(h, edge_index)    # h: (batch, n_genes, hidden_size)
            h = F.relu(h)
            h = self.dropout(h)            # h: (batch, n_genes, hidden_size)
        return h                            # output: (batch, n_genes, hidden_size)

    # Helper called by forward (line 88-92):
    def _build_edge_index(self, G_gene):
        # Converts scipy sparse matrix to torch edge_index
        # shape: (2, num_edges)
        src, dst = G_gene.nonzero()
        return torch.stack([torch.tensor(src), torch.tensor(dst)], dim=0)
```

**Tensor-shape walkthrough:**
- Input `x` has shape `(batch, n_genes)` — integer gene IDs for each cell
- After `self.gene_emb(x)`, `h` becomes `(batch, n_genes, hidden_size)`
  — each gene ID is replaced by its learnable embedding vector
- Each GNN layer preserves shape: `(batch, n_genes, hidden_size)`
  throughout
- Output is the final per-gene embedding, same shape as after the first
  embedding lookup

**Edge cases:**
- When `batch=1` (single cell), shapes still hold — no special handling needed
- If `edge_index` is empty (no edges in the gene graph), the GNN reduces
  to the identity on node features
- Missing gene IDs (e.g., out-of-vocabulary) would cause an IndexError
  in `self.gene_emb(x)` — there is no explicit handling

### 3. Cross-references

**Upstream components** (what produces this component's input):
- Bulleted list, each item: `[component name]` — brief description of
  what it produces, and where that feeds into this component

**Downstream components** (what consumes this component's output):
- Bulleted list, each item: `[component name]` — brief description of
  what it consumes from this component's output

**Related files:**
- [code_map.md](code_map.md) — the general-mode code map for this paper
- [spec.md §<N>](spec.md#<anchor>) — where this component is described
  in the paper's extraction

**Example:**

**Upstream components:**
- **Input batch** — cells are sampled from `PertData` in `gears/data.py:L250`;
  each cell provides a gene index vector `x: (batch, n_genes)`
- **Gene co-expression graph** — `G_gene` is constructed in
  `data_utils.py:L112`; passed as `edge_index` to this encoder

**Downstream components:**
- **Perturbation encoder** — receives the output `h_gene` via element-wise
  addition with `h_pert` in `model.py:L89`
- **Cross-gene MLP** — consumes the combined embedding to produce per-gene
  predictions in `model.py:L120`

**Related files:**
- [code_map.md](code_map.md)
- [spec.md §6.1 — Training](spec.md#61-training)