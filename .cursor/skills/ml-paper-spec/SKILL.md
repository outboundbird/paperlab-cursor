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

**Column rules (apply when populating the tables below):**

- **Caption column: verbatim from the paper, first sentence only, trimmed to ≤ 200 chars. No edits, no paraphrasing, no clean-ups.** This column is the user's anchor to the original document — corruption here destroys trust in the whole spec.
- **Role column: derived by the dissector** via the two-pass procedure below.
- **Components shown column: derived from the prose paragraphs that reference the figure**, not from the caption. The caption frequently omits component names that the surrounding prose makes explicit (e.g., Figure 8's caption is "Flow diagram of our Agent model" but the §2.4 prose around it names V, M, C, env explicitly). List components using the paper's own short names (V, M, C, $\theta_g$, etc.).

**Role vocabulary** (controlled, one of):

- `headline` — the figure that shows the paper's full **data-flow / computation graph** end-to-end (arrows, intermediate quantities, all components wired up). **At most one** per paper. If no single figure shows the full flow, leave Role blank for every figure and add `⚠️ UNCERTAIN: no single architecture figure`.
- `thumbnail` — a high-level "three boxes" overview that names the components but does NOT show the actual data flow. Often appears in §1 or §2 *before* the headline. Tag as `thumbnail`, not `headline`, even if it's earlier in the paper.
- `result` — any figure or table reporting numerical or empirical results (cross-method comparison tables, score histograms, transfer-back evaluations, training curves of the final method, ...). The dissector does **not** rank `result` entries; downstream agents pick whichever fits their slide. There is no `headline-results` tag — "is this *the* result" is a question for downstream agents, not the dissector.
- `ablation` — ablation study (this paper's method with one component disabled or replaced).
- `qualitative` — qualitative examples / rollouts / samples that are not numerical results (dream rollouts, sketches, attention maps, generated samples).
- `training-detail` — tensor-shape tables, layer specifications, optimizer schedules, anything documenting *how* the method was trained that isn't itself a result.
- `other` — related-work diagrams, historical context, illustrative analogies, anything else.

## Two-pass role assignment

The dissector assigns roles in two passes. Pass 1 is a cheap mechanical filter; Pass 2 is a semantic check against the prose the dissector just read.

### Pass 1 — caption-keyword pre-filter (for `headline` only)

Score each candidate caption with the following signals; the top scorer is the `headline` *candidate*:

| Signal in caption | Score |
|---|---:|
| Contains *flow diagram*, *flow chart*, *data flow*, *computation graph*, *schematic*, *pipeline* | +3 |
| Contains *full model*, *complete architecture*, *end-to-end*, *training procedure*, *inference procedure* | +2 |
| Contains *architecture*, *framework*, *system* | +1 |
| Contains *consists of*, *components*, *modules*, *parts*, *building blocks* | 0 |
| Caption ≤ 12 words AND contains *our agent*, *our model*, *our method* with no flow keywords | −1 |
| Single component named in caption (e.g., "Flow diagram of a Variational Autoencoder") | −2 |
| Caption ≤ 8 words AND no flow keywords | −1 |

Ties → prefer lower figure number.

### Pass 2 — prose cross-check (mandatory)

Pass 1 narrows; Pass 2 confirms. The dissector has already read the full PDF — it must use that semantic context, not rely on captions alone.

**`headline` cross-check.**

1. Locate the prose passage(s) in §2 (Agent Model / Method / Contribution) or §6 (Algorithm) that introduce the architecture end-to-end. These are the passages naming **more than one component in a single sentence describing how data flows between them** (e.g., "the encoder $V$ produces $z_t$, which the predictor $M$ uses to forecast $z_{t+1}$, fed to the controller $C$").
2. List every figure number cited from those passages.
3. **Reconcile:**
   - If the Pass 1 top scorer appears in those passages → confirm as `headline`. Done.
   - If a *lower*-scoring candidate appears in those passages and the Pass 1 winner does not → the prose wins; use the prose-confirmed figure as `headline`. Demote the Pass 1 winner to `thumbnail` if it shows components without flow, else `other`.
   - If multiple candidates appear in those passages, tag the one cited in the *flow-describing* sentence as `headline` and the one cited in the *enumeration* sentence as `thumbnail` (e.g., for WorldModel, Fig 4 is cited as "three components: V, M, C" → thumbnail; Fig 8 is cited as "the flow between V, M, C" → headline).
   - If no figure is cited from those passages → flag `⚠️ UNCERTAIN: no figure cited in architecture description; headline left blank`.

**`result` cross-check.**

Every figure/table the dissector wants to tag `result` must be referenced in §9 Results (or the equivalent evaluation section). If a figure is *only* referenced in §6 / methods / appendix and never in Results, it is **not** a `result` — it's a `training-detail` or `other`.

**`Components shown` cross-check.**

For each figure, the dissector locates every prose paragraph that references the figure's number (e.g., "as shown in Figure 8", "(Fig. 8)"). The components named in those paragraphs populate the `Components shown` column. Do NOT use only the caption — captions often omit component names.

### Worked example — WorldModel

**Pass 1 scores (top candidates):**

- Fig 8: "Flow diagram of our Agent model." → +3 (*flow diagram*) +2 (*full model* implied) = **+5**.
- Fig 5: "Flow diagram of a Variational Autoencoder (VAE)." → +3 (*flow diagram*) −2 (single component) = **+1**.
- Fig 4: "Our agent consists of three components..." → 0 (*consists of*, *components*) −1 (*our agent* no flow keyword) = **−1**.

Pass 1 winner: Fig 8.

**Pass 2 prose cross-check (headline):**

- §2 Agent Model prose: "Our agent has three components: V, M, C (see Figure 4) ... A full flow of how these three components interact is shown in Figure 8 ..."
- Cited figures: Fig 4 (enumeration sentence), Fig 8 (flow-describing sentence).
- Reconciliation: Pass 1 winner (Fig 8) is cited in the flow sentence → **`headline` confirmed**. Fig 4 is cited in the enumeration sentence → **`thumbnail`**.

**Pass 2 prose cross-check (result):**

- §9 Results prose references: Table 1 (CarRacing scores vs methods), Fig 25 (cumulative-reward histogram of this paper's method), Fig 29 (Doom survival histogram). All three appear in Results → all three tagged `result`.
- Fig 22 ("Description of tensor shapes at each layer of ConvVAE") is referenced only in Appendix A.2, never in §9 → **`training-detail`**, not `result`.

**Pass 2 prose cross-check (Components shown for Fig 8):**

- Caption says only "Flow diagram of our Agent model."
- §2.4 prose around the citation says "the world model V encodes $x_t$ to $z_t$; the MDN-RNN M predicts $z_{t+1}$ from $(z_t, a_t, h_t)$; the controller C maps $[z_t; h_t]$ to $a_t$, which the environment env consumes."
- → `Components shown: V, M, C, env`.

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
