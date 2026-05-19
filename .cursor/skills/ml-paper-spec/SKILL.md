---
name: ml-paper-spec
description: Defines the `spec.md` schema for structured extraction of ML methods papers. `spec.md` is written to the vault at `vault_path(slug, "spec.md")`. Use when dissecting, parsing, summarizing, or creating a paper spec.
---

# ML Paper Spec Schema

## Purpose

This file defines the schema for `spec.md`, the structured extraction of an ML methods paper. `spec.md` is produced by the Dissector subagent and consumed by downstream subagents such as Explainer, Implementer, and Critic. A consistent schema across papers lets downstream subagents know where to look for any given piece of information.

## Reading the PDF

Always extract paper text via `tools.pdf.extract_pdf_text`, which uses
`pypdf` (pinned in `requirements.txt`) with a `pdftotext` fallback and
caches to `papers/<slug>/.cache/paper.txt`. Do **not** invent ad-hoc
extraction with other libraries.

Python:

```python
from tools.pdf import extract_pdf_text
text = extract_pdf_text(slug)
```

Shell:

```bash
python -m tools.pdf extract <slug>          # prints text, caches result
python -m tools.pdf extract <slug> --refresh  # force re-extract
```

For supplements, pass an explicit `pdf_path=` and a unique `source=` name
so the cache files don't collide.

## Listing figures and tables

To populate §4.5 (Figures & Tables), call `tools.figures.list_figures`:

```python
from tools.figures import list_figures
for c in list_figures(slug):
    print(c.kind, c.number, c.page, c.caption)
```

Shell:

```bash
python -m tools.figures list <slug>
```

This walks every page of the PDF and parses caption lines matching `Figure N: ...` and `Table N: ...`. The Dissector then assigns each entry a `Role` per the controlled vocabulary in §4.5.

## Conventions

Global rules that apply to all sections:

- Use LaTeX, not Unicode math
- Flag uncertainty with ⚠️ UNCERTAIN: prefix
- Target length: 2-4 pages

## Document header

Every `spec.md` must begin with:

```markdown
---
paper: <slug>
category: model
tags:
- AI-guided-paper-reading
- paper-overview
---

# <slug> Overview

**Paper:** <full title>
**Authors:** <author list>
**Venue:** <journal/conference, year, pages>
**DOI:** <full DOI URL if available>

---
```

## Subsection numbering
Use numeric values such as 6.1, 6.1.1.

## Required sections (in this order)

### 1. Context

One paragraph. What domain does this paper operate in, and what open
challenge motivates the work?

### 2. Contribution

One or two sentences. What does the paper add to address that challenge?

### 3. Problem setup/ objective

Write up the problem set up with a paragraph. Produce both an informal and a formal problem setup.
For example:
**Informal:** Given a set of observed single-cell gene expression perturbations,
predict the transcriptional response to perturbations not seen during training,
including combinations of perturbations.

**Formal:**

- *Input:* dataset $\mathcal{D} = \{(g_i, \mathcal{P}_i)\}_{i=1}^N$ where...
- *Output:* predicted post-perturbation expression $\hat{g}$ for a query
  perturbation $\mathcal{P}^* \notin \mathcal{P}_{\text{train}}$
- *Evaluation:* mean squared error on held-out perturbations, ...

### 4. Assumptions

Use bullet points to summarize the assumptions in the paper. Number assumptions with labels A1, A2, A3... so other documents can cross-reference them.
For example:

- **A1:** The gene co-expression graph $\mathcal{G}_{\text{gene}}$ is
  informative of perturbation response similarity.
- **A2:** Perturbation effects are approximately additive across combined
  perturbations.
- (If no assumptions found: "No explicit assumptions stated in the paper.")

### 4.5 Figures & Tables

Catalog every figure and table the paper contains. Downstream subagents (especially the Visualizer) rely on this section to know *what the paper itself shows* — without it they can only synthesize new diagrams from the prose and routinely miss the canonical architecture figure (which may appear late in the paper, not as Figure 1).

Populate the two tables below by calling `tools.figures.list_figures(slug)` (which parses captions from the cached PDF text). The Dissector adds the `Role` and `Components shown` columns by reading each caption and matching it against the paper's prose.

**Role vocabulary** (controlled, one of):

- `headline` — the figure that shows the entire architecture / mechanism end-to-end. **At most one** per paper. If no single figure captures the whole architecture, leave Role blank for every figure and add a `⚠️ UNCERTAIN: no single architecture figure` note above the table.
- `thumbnail` — a smaller / partial version of the headline figure (often used in the intro).
- `headline-results` — the table or figure showing the paper's main quantitative claim.
- `ablation` — ablation study.
- `qualitative` — qualitative examples / rollouts / samples.
- `baseline-comparison` — head-to-head comparison plot/table against prior methods.
- `training-detail` — loss curves, training-dynamics plots, learning-rate schedules.
- `other` — anything else.

**Heuristics for `headline` identification.** Look for captions containing *overview, architecture, system, framework, pipeline, end-to-end, full model, schematic, flow diagram*. Cross-reference: the headline figure is typically the one the abstract or §2 Contribution paragraph cites first. If two figures jointly cover the architecture (e.g., one for training, one for inference), tag the one referenced earlier as `headline` and the other as `thumbnail`.

#### Figures

| # | Page | Caption (first sentence, verbatim) | Role | Components shown |
|---|------|------------------------------------|------|------------------|
| 1 | 1 | A World Models agent receives observations from the environment... | thumbnail | V, M, C |
| 4 | 5 | Flow diagram of V → M → C interaction during one timestep. | **headline** | V, M, C |
| 7 | 8 | Car Racing rollout examples at τ=1.15. | qualitative | env, agent |

#### Tables

| # | Page | Caption (first sentence, verbatim) | Role |
|---|------|------------------------------------|------|
| 1 | 7 | Car Racing scores across baselines. | headline-results |
| 2 | 9 | Doom survival times by temperature τ. | ablation |

### 5. Notation

Produce a two-column markdown table with columns `Symbol | Meaning`.

Rules:

- Use standard LaTeX between `$...$` (inline) and `$$...$$` (display), never Unicode math characters; never `\(... \)` or `\[ ... \]`
  Write `$\mathcal{D}$` not `𝒟`, `$\theta_g$` not `θg`.
- Include domain/type information inline in the Meaning column when the
  paper provides it (e.g., "gene expression vector, $\in \mathbb{R}^K$").
- Include every symbol that appears more than once in the paper.
- If the paper uses inconsistent notation (common), pick one form and flag
  the inconsistency with ⚠️ UNCERTAIN.
- Each `\tag{}` refers to exactly one equation number from the paper — do not combine multiple numbers in a single tag

Example:

| Symbol | Meaning |
|--------|---------|
| $\mathcal{D} = \{(g_i, \mathcal{P}_i)\}_{i=1}^N$ | training dataset of $N$ cells |
| $g_i \in \mathbb{R}^K$ | gene expression vector for cell $i$, $K$ genes |
| $\mathcal{G}_{\text{gene}}$ | gene co-expression graph |

### 6. Algorithm

Produce two views of the algorithm, in this order: a condensed pseudo-code
view for quick reference, then a detailed nested-bullet view for pedagogy.

If the paper describes multiple distinct procedures (training and inference,
for instance), repeat both views for each procedure under its own subsection.

**Equation fidelity (hard rule).** Quote equations *exactly* as the paper presents them. Do NOT silently merge implementation details from algorithm boxes (clipping, squashing, scaling, normalization, gradient stops, weight decay) into the formal definition equation. The definition and the deployment form are different objects:

- The **definition** is the equation in the methods section (e.g., `a_t = W_c [z_t h_t] + b_c`).
- The **deployment form** is what the algorithm box / training pseudo-code actually computes (e.g., `a_t_clipped = tanh(W_c [z_t h_t] + b_c)`).

If the two differ, record both under the component, with explicit labels:

```markdown
- **Controller (C):**
  - Purpose: maps latent + recurrent state to action.
  - Definition (Eq. 1): $a_t = W_c [z_t\;h_t] + b_c$
  - Deployment form (§6.2 algorithm): a `tanh` squashing is applied so
    actions fit the environment's allowed range.
```

Never combine them into a single equation like `a_t = tanh(W_c[z_t h_t] + b_c)` — that misrepresents the paper's formalism. When in doubt, the definition wins; flag the deployment difference with `⚠️ UNCERTAIN: deployment form may diverge` if the paper is vague.

**Pseudo-code view** — a fenced code block:

\`\`\`
Input: D = {(g_i, P_i)}, gene graph G_gene, GO graph G_GO

1. Construct perturbation similarity graph G_pert from G_GO
2. For each (g_i, P_i) in D:
   a. h_gene = GNN_θg(g_i, G_gene)
   b. h_pert = GNN_θp(P_i, G_pert)
   c. ŷ_i = MLP(h_gene, h_pert)
3. Update θ to minimize ‖ŷ - g_post‖²
\`\`\`

**Detailed components** — nested bullets with purpose and formula:

- **Gene co-expression graph encoder:**
  - Purpose: capture relative heterogeneity of perturbational response
  - Formula: $h_{\text{gene}} = \text{GNN}_{\theta_g}(x_{\text{gene}}, \mathcal{G}_{\text{gene}})$
- **Perturbation encoder using GO:**
  - Purpose: ...
  - Formula: ...

### 7. Hyperparameters

Create a table with four columns: Hyperparameter, Symbol, Value used in paper, Role. Include only hyperparameters — values a practitioner chooses before training (learning rate, hidden dimension, number of layers, batch size, etc.). Do **not** include learned parameters like $\theta$, $W$ or model weights; those go in the Notation section.

For example:

|Hyperparameter  | Symbol|   Value|Role|
|----------------|-------|--------|----|
|Hidden dimension|   $d$ |  64    |Width of GNN and MLP layers|

### 8. Datasets

A table with name, size, source, what task they're used for, which baselines are compared on them if available. One dataset per row, if the paper use multiple datasets.

for example:

|Dataset|Size|Source|Task|Baselines compared|
|-------|----|------|----|------------------|
|Norman et al. 2019|284 perturbations, 108K cells|Perturb-seq|Single-gene perturbation prediction|scGen, CPA|

### 9. Results/ Claims

Produce two subsections, in this order. Either may be empty if the paper
has no entries for that type — state "None stated" if so.

**Theoretical claims** — a numbered list. Each entry includes the claim
statement, the assumptions it depends on, and a pointer to where it's proved.

- **Claim 1** (Proposition 3.1): Under assumption A2, ...
  *Proof in §3.3 / Appendix B.*

**Empirical results** — a table comparing methods on metrics.

| Dataset | Method | Metric | Value |
|---|---|---|---|
| Norman 2019 | GEARS | Pearson r | 0.78 |
| Norman 2019 | scGen | Pearson r | 0.62 |

### 10. Limitations

A bullet list of limitations acknowledged by the authors (typically found in Discussion, Limitations, or Future Work sections). Include only limitations the authors themselves state — do not infer or invent limitations. If no limitations are stated: "No limitations stated by authors."

for example:

- **Biological interpretability of latent features:** The paper acknowledges that building biological interpretations of the latent axes (e.g., which features distinguish responders from non-responders) requires additional analysis beyond what scGen itself provides.
