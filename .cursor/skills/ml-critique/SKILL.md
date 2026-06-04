---
name: ml-critique
description: Defines the `critic_reviews.md` audit schema for calibrating trust in ML papers by reviewing claims, evidence, reproducibility, and paper-code alignment. `critic_reviews.md` lives at `vault_path(slug, "critic_reviews.md")`. Two backend-only gate modes return PASS/FAIL without writing a file: blueprint-check (pre-emission, invoked by the implementer) and extraction-fidelity (pre-run, invoked by the experimenter for Stage-2 component surgery). Use when auditing, critiquing, reviewing, or trust-calibrating a PaperLab paper, or gating reconstructed/extracted code.
---

# ML Critique Schema

## Purpose

This file defines the schema for `critic_reviews.md`, the structured audit that helps the user calibrate trust in a paper. `critic_reviews.md` is produced by the Critic subagent and lives at `vault_path(slug, "critic_reviews.md")` (resolved via `tools/paths.py`).

The audit covers two scopes: paper methodology (claims, evidence,
unstated limitations) and paper-code alignment (what the implementation
actually does vs. what the paper says).

## Audit source: official vs reconstructed

The audit reads `code_map.md`, which maps one of two code sources (see
`ml-code-map` "Two sources, one schema"). Read its §1 **Source** field
and adapt:

- **`official`** — the implementation is the authors' upstream code. §3
  audits **author choices**; §4 checks upstream/dataset/training
  reproducibility. This is the original behavior.
- **`reconstructed`** — the implementation is the `coder`'s Stage-1
  `method.py`, built from the paper via `code_blueprint.md`. There is no
  third-party author. §3 becomes a **fidelity** audit (does the
  reconstruction drift from the paper's math?); §4 swaps the
  upstream/dataset/training rows for reconstruction-fidelity rows. The
  §2 claims audit and the independent-spec-reading firewall are
  unchanged. This is the **hop-2-vs-spec firewall**: the critic re-reads
  the spec independently to check code the critic did not write.

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
paper: <slug>
category: model
agent: critic
tags:
- AI-guided-paper-reading
- critic-review
---

# Critic Reviews — <slug>

**Paper:** <paper title>
**Paper context:** one-sentence summary of what the paper does
**Source:** `official` or `reconstructed` (from `code_map.md` §1)
**Code location:** for `official` — absolute path from `repo_upstream_dir(slug)` + source URL (<URL>); for `reconstructed` — absolute path from `vault_code_dir(slug)`
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
Discrepancy entry. The gotcha itself lives in code_map.md; this section
adds two fields on top.

**Source-dependent framing:**

- **`official`** — discrepancies are author choices (code-vs-paper). Use
  the entry format below as-is.
- **`reconstructed`** — discrepancies are **fidelity findings** (does the
  coder's reconstruction drift from the paper's math?). Same two added
  fields, but "Functional role" describes what the reconstructed block
  does and "What would resolve uncertainty" points at the relevant
  invariant in `test_invariants.py` or a spec re-check, not a re-run
  against the authors' benchmark. If `code_map.md §5` reports no fidelity
  gaps, state in §3 that the reconstruction is faithful and there are no
  discrepancies to analyze — do not manufacture any.

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
Each row is verifiable from spec.md §7 and code_map.md. Do not introduce status assessments that are not grounded in those files. **The row set depends on the source.**

**`official` source** — a binary (yes / no / partial) check on each item, verifiable from files on disk:

| Item | Status | Notes |
|------|--------|-------|
| Upstream code available | yes / no | absolute path from `repo_upstream_dir(slug)` if yes |
| Datasets accessible without authentication | yes / no | source link |
| All hyperparameters from spec.md §7 documented in code or config | yes / no / partial | which are missing |
| Random seeds fixed in training code | yes / no | grep result |
| Train/val/test splits explicitly defined | yes / no | location in code |
| Evaluation metrics clearly defined in code | yes / no | which file |

**`reconstructed` source** — there is no upstream repo, dataset, or
training run, so those rows do not apply. Substitute fidelity rows,
verifiable from `vault_code_dir(slug)`:

| Item | Status | Notes |
|------|--------|-------|
| Reconstructed code present (`method.py`) | yes / no | `vault_code_dir(slug)` |
| Invariant tests present and passing (`test_invariants.py`) | yes / no / partial | N invariants; any failing |
| Every spec.md §6 component present in `method.py` | yes / no / partial | which are missing (cross-ref code_map coverage) |
| All hyperparameters from spec.md §7 exposed in the `Method` constructor | yes / no / partial | which are missing |
| Random seeds fixed in the invariant test | yes / no | grep result |
| `⚠️ UNCERTAIN` quantities flagged (blueprint/code) | yes / no | which, and the default chosen |


### 5. Cross-references


A short list of links that help the reader navigate between code_map.md and spec.md for each claim and discrepancy.
- **Claim 1**: spec.md §1 (intro), code_map.md §2 (forward pass)
- **Claim 2**: spec.md §7.1, code_map.md §2 (forward pass), code_map.md §3 (training loop)
- **Discrepancy 1** (cross-gene MLP input dimensionality): code_map.md §5 gotcha #1, code_map.md §2 (cross-gene embedding), spec.md §6.1 step 4e

## Blueprint-check mode

A second, **backend-only** mode of the Critic, invoked by the
`implementer` during blueprint generation (`ml-blueprint` skill). It
audits a **draft `code_blueprint.md`** *pre-emission* — before the file
is written — and returns a **PASS/FAIL verdict with findings**. It
writes **no file** (it does not produce `critic_reviews.md` or any
artifact). This is the hop-1 guard in the two-hop fidelity model
(`log/2026-06-03-implementer-coder-blueprint-design.md`).

### Independence is the whole point

The Critic must build its **own** representation of the paper's math from
`spec.md` (and the PDF only where the spec is ambiguous), and check the
draft against *that*. It does **not** treat the draft's §3 steps or §4
invariants as given, and does **not** share the implementer's working
memory. The check has value only because the two representations are
derived independently — the generator/discriminator firewall from the
2026-06-02 two-memory design. Build the independent consequence list
*before* studying the draft's §4 closely, to avoid anchoring on it.

### What the Critic derives independently

The same "consequence list" discipline as audit mode, applied to
implementation rather than claims:

- **Shapes** of each named quantity through the forward pass.
- **Signs / ranges** the math implies (a softmax output is in `[0,1]`; a
  norm-based loss is `≥ 0`).
- **Normalization / conservation** (a softmax is row-stochastic over a
  specific axis; probabilities sum to 1).
- **Invariances / equivariances / limits / monotonicity** the method's
  math entails (permutation-equivariance, a temperature limit, etc.).

Carry the `[A]` (mechanical consequence) / `[B]` (scope) inference
discipline. `[C]` field-level critique remains **forbidden** — judge the
draft against the paper's own math, not against outside work.

### Verdict rules

- **FAIL** — at least one of:
  - `[CONTRADICTION]`: a draft §4 invariant contradicts the math (e.g.
    normalization over the wrong axis, an impossible sign or range).
  - `[INCONSISTENT-STEP]`: a draft §3 step cannot follow from the spec's
    math.
- **WARN (does not flip the verdict)**:
  - `[MISSING-INVARIANT]`: a property the Critic derived that the draft
    should assert but omits. Completeness is not provable, so a missing
    invariant is a suggestion, not a failure (mirrors how an
    `unresolved` citation warns but does not block).
  - `[UNSUPPORTED]`: a draft claim not grounded in the spec/PDF.
- **PASS** — no `[CONTRADICTION]` and no `[INCONSISTENT-STEP]`. Warnings
  may still be present and should be reported so the implementer can act
  on them.

### Scope: what this mode does NOT do

- It does **not** check that the draft lists *enough* invariants
  (completeness is unprovable — hence `[MISSING-INVARIANT]` only warns).
  This yields strong **consistency**, not a correctness proof — the same
  stance as the two-memory design.
- It does **not** check runnable code (there is none yet; that is the
  Coder's hop-2 concern, guarded by invariants-as-assertions).
- It does **not** judge the method against the broader field (`[C]`
  forbidden).

### Reporting back (to the implementer)

Return, without writing a file:

- **Verdict:** PASS or FAIL.
- **Findings:** each tagged `[CONTRADICTION]` / `[INCONSISTENT-STEP]`
  (fail) or `[MISSING-INVARIANT]` / `[UNSUPPORTED]` (warn), each naming
  the draft §/step and the spec reference, specific enough for the
  implementer to revise directly.

The implementer owns the retry loop (max 2) and the escalation to the
user; the Critic only returns verdicts.

## Extraction-fidelity mode

A third, **backend-only** mode of the Critic, invoked by the
`experimenter` during a Stage-2 experiment (the coder's component-surgery
mode, `ml-experiment-code` § Stage 2). It audits **experiment code
pre-run** — before the experiment is trusted — and returns a
**PASS/FAIL verdict with findings**. It writes **no file**. Design:
[`log/2026-06-04-stage2-regime2-component-surgery-design.md`](../../../log/2026-06-04-stage2-regime2-component-surgery-design.md).

The Stage-2 experiment holds a shared **principle** fixed in a synthesized
`scaffold.py` and swaps each paper's **divergent component**, extracted
into `repo_experiments_dir(topic)/methods/<slug>/extracted.py`. Both the
extracted components and the scaffold are agent-invented and must be
checked. This mode has two checks.

### Check A — extraction fidelity (per paper, the hard gate)

For each `methods/<slug>/extracted.py`: does it still compute the paper's
mechanism, or did the extraction/refactor alter it? This is the same
firewall as the reconstructed-source audit — the Critic builds its **own**
representation of the component from the paper, independently of the
coder's extraction.

- **Anchors:** `code_map.md` (primary — it points at the exact source
  lines the component was lifted from) and `spec.md` (secondary — the
  described mechanism). Resolve vault paths via the CLI first.
- **What to check:** the extracted logic against the source it claims
  (provenance header names the `code_map.md §` and lines). Confirm no
  added terms, no dropped terms, no swapped distribution/op, no changed
  constants or ordering. Allowed differences are only I/O reshaping to the
  scaffold slot (rename, reshape, device).
- Carry the `[A]`/`[B]` discipline; `[C]` field critique forbidden. Judge
  the extraction against the paper's own math, not outside work.

### Check B — scaffold fidelity

For `scaffold.py`'s fixed part (encoder/readout/objective form): does it
faithfully represent the **shared principle** the papers claim (e.g. is
the IB objective $I(X;Z) - \beta I(Z;Y)$ rendered correctly)? A wrong
scaffold measures every variant under a wrong objective, invalidating the
whole comparison.

### Behavioral-equivalence evidence (from the coder)

When the coder was able to run a component in isolation, it passes a
behavioral-equivalence result (original vs. extracted on seeded synthetic
input). Treat a PASS as **corroborating** Check A and a FAIL as a
`[CONTRADICTION]`. Its **absence is not a failure** (often infeasible) —
fall back to the static audit. The Critic owns the verdict either way.

### Verdict rules

- **FAIL** — at least one of:
  - `[EXTRACTION-DRIFT]`: an `extracted.py` adds/drops/swaps logic vs. its
    cited source (Check A), or a behavioral-equivalence check the coder ran
    failed.
  - `[SCAFFOLD-DRIFT]`: `scaffold.py`'s fixed part misrepresents the shared
    principle (Check B).
- **WARN (does not flip the verdict)**:
  - `[PROVENANCE-GAP]`: a provenance header is missing or its cited
    `code_map.md §`/lines do not match what was extracted (makes the audit
    harder; flag but do not fail on this alone).
  - `[UNVERIFIABLE]`: the source could not be located to confirm fidelity
    (e.g. `code_map.md` missing for that paper) — report so the
    experimenter can resolve, but do not invent a verdict.
- **PASS** — no `[EXTRACTION-DRIFT]` and no `[SCAFFOLD-DRIFT]`. Per-paper:
  a single drifting component fails **that variant**, not the whole
  experiment.

### Scope: what this mode does NOT do

- It does **not** judge whether the comparison is *interesting* or the
  seam well-chosen — that is the experimenter + user's design decision.
- It does **not** check that the experiment will produce good results —
  only that the extracted components are faithful and the scaffold
  represents the shared principle.
- It does **not** run the experiment or write any file.
- `[C]` field-level critique remains forbidden.

### Reporting back (to the experimenter)

Return, without writing a file:

- **Verdict:** PASS or FAIL, **per paper** for Check A, plus the single
  Check B verdict for the scaffold.
- **Findings:** each tagged `[EXTRACTION-DRIFT]` / `[SCAFFOLD-DRIFT]`
  (fail) or `[PROVENANCE-GAP]` / `[UNVERIFIABLE]` (warn), each naming the
  file, the `code_map.md §`/spec reference, and what drifted — specific
  enough for the coder to fix the extraction directly.

The experimenter owns the retry loop (max 2, fix → re-audit), the
escalation to the user, and the `findings.md` record of a blocked variant;
the Critic only returns verdicts.
