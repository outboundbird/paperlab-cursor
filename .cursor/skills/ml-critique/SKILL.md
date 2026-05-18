---
name: ml-critique
description: Defines the `critic_reviews.md` audit schema for calibrating trust in ML papers by reviewing claims, evidence, reproducibility, and paper-code alignment. `critic_reviews.md` lives at `vault_path(slug, "critic_reviews.md")`. Use when auditing, critiquing, reviewing, or trust-calibrating a PaperLab paper.
---

# ML Critique Schema

## Purpose

This file defines the schema for `critic_reviews.md`, the structured audit that helps the user calibrate trust in a paper. `critic_reviews.md` is produced by the Critic subagent and lives at `vault_path(slug, "critic_reviews.md")` (resolved via `tools/paths.py`).

The audit covers two scopes: paper methodology (claims, evidence,
unstated limitations) and paper-code alignment (what the implementation
actually does vs. what the paper says).

## Reading the PDF

When the spec or code_map references the PDF ambiguously and you need to
consult the paper text, extract it via `tools.pdf.extract_pdf_text`, which
uses `pypdf` with a `pdftotext` fallback and caches to
`papers/<slug>/.cache/paper.txt`. Do **not** invent ad-hoc extraction.

```python
from tools.pdf import extract_pdf_text
text = extract_pdf_text(slug)
```

```bash
python -m tools.pdf extract <slug> [--refresh]
```

## Conventions

- **Audience:** reader who has already read spec.md and code_map.md.
  Assume familiarity with the paper's terminology and method.
- **Posture:** annotator, not judge. Surface material that bears on trust calibration. Do not classify findings as "good" or "bad."
- **Inference types:** when extending beyond what the paper states, prefix the inference with its type:
  - `[A] Mechanical:` — a consequence that follows from a stated limitation by the paper's own framework
  - `[B] Scope:` — an observation about what experiments cover or don't cover, where the comparison reference is named in the paper itself (e.g., "compared X but not Y, where Y is mentioned in related work")
  - **Forbidden:** `[C]` field-level critique. Do not introduce
    limitations based on general field knowledge or comparison to work the paper does not reference.
- **Sources:** spec.md and code_map.md are primary. The PDF is
  consulted only when the spec or code_map references something
  ambiguously.
- **Length target:** 2–4 pages. Longer than spec.md, shorter than code_map.md.
- **math notation**: when citing equations in claims/discrepancies, use `$ ... $` for inline math and `$$ ... $$` for display math. Never use `\( ... \)` or `\[ ... \]`.

## Required sections

### 1. Paper context (header)

Every critic_reviews.md must begin with a header in this format:

```markdown
---
category: model
tags:
- AI-guided-paper-reading
- critic-review
---

# Critic Reviews — <slug>

**Paper:** <paper title>
**Paper context:** one-sentence summary of what the paper does
**Repo:** absolute path from `repo_upstream_dir(slug)`, source URL (<URL>),
**Audit date:** MM/DD/YYYY
**Sources audited**: spec.md, code_map.md

---
```

### 2. Core claims audit

For each major claim in the paper, populate this format:

**Claim N: [one-sentence claim]**
- **Where stated:** spec.md §X / paper section
- **Evidence cited:** tables, figures, and experiments referenced in the
  paper or summarized in spec.md
- **What the evidence covers:** the specific scope established by the
  cited experiments — datasets used, cell types, perturbation types,
  range of perturbation sizes, baselines compared. State only what
  the experiments actually establish, not what the paper claims more
  broadly.
- **What the evidence does not cover:** dimensions not tested by the
  cited experiments. Use [A] or [B] inference-type prefixes when
  extending beyond what's stated.
- **Load-bearing for adoption:** yes / partial / no, with a one-sentence
  justification framed around the user's adoption decision (not the
  field's interest in the claim).

**Worked example:**

**Claim 1: GEARS can predict transcriptional response to unseen gene perturbations.**
- **Where stated:** spec.md §1, paper abstract and introduction
- **Evidence cited:** Figure 2, Table 1, paper results section; experiments described in spec.md §7.1
- **What the evidence covers:** Performance on held-out single-gene and held-out two-gene perturbations from the Norman et al. 2019 Perturb-seq dataset (K562 cell line, ~5,000 cells, ~150 distinct perturbations).
- **What the evidence does not cover:** [B] Scope: performance on other Perturb-seq datasets (Replogle, Adamson — both mentioned in the paper's related work) is not tested. [B] Scope: performance on perturbations larger than 2 genes is not tested. [A] Mechanical: since training requires perturbations to be in the GO graph, perturbations of genes not annotated in GO are out-of-scope by construction.
- **Load-bearing for adoption:** Yes. If the user wants to use GEARS to screen unseen perturbations in their own work, this claim is the value proposition. If unsupported on non-Perturb-seq data or larger perturbation sets, the practical utility for that user drops significantly.

### 3. Paper-code alignment

For each gotcha listed in `code_map.md §5 Gotchas`, produce one
Discrepancy entry. The gotcha itself (paper-says / code-does / why-it-
matters) lives in code_map.md; this section adds two fields on top:

**Discrepancy N: [short label, matching the gotcha]**
- **Source:** code_map.md §5 (link to the specific gotcha)
- **Functional role in the architecture:** what does this part of
  the code control? Why might its behavior differ from the paper's
  formula?
- **What would resolve uncertainty:** a specific test, code
  modification, or comparison that would confirm whether this matters
  for adoption

The two added fields are Critic's contribution. The gotcha itself is
not restated — link to it in code_map.md.

for example:

**Discrepancy 1: Cross-gene MLP input dimensionality**
- **Source:** code_map.md §5, gotcha #1
- **Functional role in the architecture:** `cross_gene_state` produces
  the shared embedding $\mathbf{h}^{\text{CG}}$ that augments per-gene
  predictions. By feeding scalar $z_u$ rather than the d-dimensional
  $\mathbf{h}_u^{\text{post-pert}}$, the code discards d-1 dimensions
  of per-gene context before cross-gene mixing. The paper's formula
  preserves that context.
- **What would resolve uncertainty:** Modify the code to use the full
  d-dimensional post-perturbation vectors as input to `cross_gene_state`
  (input shape K×d → d). Compare on the same Norman et al. benchmark.
  If results are similar, the simplification is harmless. If the
  modified version substantially outperforms, the paper's formula is
  the better architecture and the code is suboptimal.

### 4. Reproducibility checklist
Each row is verifiable from spec.md §7 and code_map.md. Do not introduce status assessments that are not grounded in those files.

A binary (yes / no / partial) check on each item, verifiable from files on disk, for example:

| Item | Status | Notes |
|------|--------|-------|
| Upstream code available | yes / no | absolute path from `repo_upstream_dir(slug)` if yes |
| Datasets accessible without authentication | yes / no | source link |
| All hyperparameters from spec.md §7 documented in code or config | yes / no / partial | which are missing |
| Random seeds fixed in training code | yes / no | grep result |
| Train/val/test splits explicitly defined | yes / no | location in code |
| Evaluation metrics clearly defined in code | yes / no | which file |


### 5. Cross-references


A short list of links that help the reader navigate between code_map.md and spec.md for each claim and discrepancy.
- **Claim 1**: spec.md §1 (intro), code_map.md §2 (forward pass)
- **Claim 2**: spec.md §7.1, code_map.md §2 (forward pass), code_map.md §3 (training loop)
- **Discrepancy 1** (cross-gene MLP input dimensionality): code_map.md §5 gotcha #1, code_map.md §2 (cross-gene embedding), spec.md §6.1 step 4e
