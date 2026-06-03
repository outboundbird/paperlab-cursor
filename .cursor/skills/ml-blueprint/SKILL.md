---
name: ml-blueprint
description: Defines the `code_blueprint.md` schema — a framework-agnostic implementation contract reconstructed from an ML paper's math when no official code exists. Written by the Implementer subagent to `vault_path(slug, "code_blueprint.md")`, gated pre-emission by the Critic. Consumed by the Coder to write runnable code. Use when reconstructing a paper's method as an implementation contract without an upstream repository.
---

# ML Blueprint Schema

## Purpose

This file defines the schema for `code_blueprint.md`: a
**framework-agnostic implementation contract** reconstructed from a
paper's mathematics when **no official code is available**. It is
produced by the Implementer subagent and written to
`vault_path(slug, "code_blueprint.md")` (resolved via `tools/paths.py`).

The blueprint is the bridge across the two-hop fidelity model:

```
paper math → [implementer] → code_blueprint.md → [coder] → runnable code
             (hop 1)                              (hop 2)
```

- **Hop 1** (paper math → blueprint) is guarded by the **Critic running
  pre-emission** with its own independent reading of the paper (see the
  gate below).
- **Hop 2** (blueprint → code) is guarded by the blueprint's **required
  invariants section**: the Coder emits each invariant as a runtime
  assertion and runs it on synthetic input before declaring done.

## Blueprint vs. code_map — keep them separate

`code_blueprint.md` is a **separate file** from `code_map.md`, never a
section inside it. The two are mutually exclusive signals:

- `code_map.md` exists → the paper shipped **official code**, mapped to
  real files and line numbers.
- `code_blueprint.md` exists → the method was **reconstructed from the
  math**; there is no official code (or the user explicitly asked for a
  from-math contract anyway).

Merging them would hide whether the paper has real code. A reader (and
the Coder) must be able to tell the two apart at a glance.

## Scope boundaries

- The blueprint is **framework-agnostic**: math, shapes, dtypes, ordered
  steps, and invariants. It does **not** contain runnable code, no
  framework-specific calls (`torch.*`, `jax.*`), no import statements,
  no class boilerplate. Writing runnable code is the Coder's job
  (hop 2).
- The blueprint does **not** claim to be the authors' implementation. It
  is a reconstruction from the paper, clearly marked as such.
- The blueprint is **information-rich on purpose**: it pins axes,
  shapes, step order, and edge cases to **minimize translation
  ambiguity** in hop 2. Vagueness here is the primary failure mode —
  every quantity that could be implemented two ways must be
  disambiguated.

## Conventions

- **Audience:** a reader fluent in ML math and Python who will translate
  this into one framework. Assume familiarity with tensors, broadcasting,
  and common layer types; do not re-explain them.
- **Source of truth:** `vault_path(slug, "spec.md")` is primary. Consult
  the PDF (via `tools.pdf.extract_pdf_text`) only when the spec is
  ambiguous on a quantity the blueprint must pin.
- **Math notation:** `$ ... $` inline, `$$ ... $$` display. Never
  `\( ... \)` or `\[ ... \]`. Never Unicode math characters in prose or
  equations.
- **Shapes:** write every tensor's shape explicitly using named
  dimensions consistent across the document (e.g. `[B, N, d]`). Define
  each symbol once in §2.
- **Axes:** when an operation reduces or normalizes over an axis
  (softmax, sum, mean, argmax), **state the axis explicitly** and back it
  with an invariant in §4.
- **Length target:** 1–6 pages. Comparable to `code_map.md`.

## Reading the PDF

When the spec is ambiguous and blueprint precision requires the paper
text, extract via `tools.pdf.extract_pdf_text` (caches to
`papers/<slug>/.cache/paper.txt`). Do not invent ad-hoc extraction.

```python
from tools.pdf import extract_pdf_text
text = extract_pdf_text(slug)
```

## Required sections

### 1. Header

```markdown
---
paper: <slug>
category: model
agent: implementer
status: blueprinted
sources:
- "[[<slug>/spec.md]]"
concepts:
- "[[<canonical-concept-name>]]"
tags:
- AI-guided-paper-reading
- code-blueprint
---

# Code Blueprint — <slug>

> **Reconstructed from the paper's mathematics. This is NOT the authors'
> official code.** No upstream repository was available (or a from-math
> contract was explicitly requested). Treat every step as a
> reconstruction to be validated against the invariants in §4.

## 1. Blueprint Info

**Paper:** <paper title>
**Paper context:** one-sentence summary of what the paper does
**Reconstructed from:** `spec.md` (+ PDF where noted)
**Blueprint date:** MM/DD/YYYY
**Target framework:** framework-agnostic (Coder selects at hop 2)

---
```

### 2. Symbols and shapes (table)

Define every quantity the forward pass and loss use, once, with shape
and dtype. This table is the contract's vocabulary; §3 and §4 reference
it.

| Symbol | Meaning | Shape | Dtype | Notes |
|---|---|---|---|---|
| $X$ | input batch | `[B, N, d_in]` | float | $B$ batch, $N$ tokens |
| $W_q$ | query projection | `[d_in, d]` | float | learnable |
| ... | ... | ... | ... | ... |

### 3. Per-component implementation contract (the main content)

For each major algorithm component (mirroring `spec.md §6`), write an
ordered, framework-agnostic step list. Each step:

- cites the paper formula from `spec.md` if available;
- states the operation in math, with **explicit axes**;
- states the **output shape** of that step (referencing §2 symbols);
- flags any edge case (masking, numerical stability, initialization).

Example component:

**Scaled dot-product attention**

**Paper formula** (from `spec.md §6`):

$$A = \mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d}}\right), \quad C = A V$$

Steps:

1. Project: $Q = X W_q$, $K = X W_k$, $V = X W_v$. Output shapes: $Q, K, V$ each `[B, N, d]`.
2. Scores: $S = Q K^\top / \sqrt{d}$. Output shape `[B, N, N]`.
3. Weights: $A = \mathrm{softmax}(S$ over the **last** axis$)$. Output shape `[B, N, N]`.
4. Context: $C = A V$. Output shape `[B, N, d]`.

Edge cases: if a padding mask is supplied, set masked entries of $S$ to
$-\infty$ **before** the softmax in step 3.

### 4. Invariants (REQUIRED — the hop-2 contract)

This section is **mandatory** and **non-empty**. It lists checkable
consequences that must hold **if the reconstruction is correct**. The
Coder turns each into a runtime assertion (shape check, value check, or
a small synthetic test) and runs them before declaring the code done. An
assertion that fails means the code does not match the blueprint.

Write invariants as **checkable claims**, grouped by type. Cover at
least shapes and any normalization/sign/range property the math implies.
Examples:

- **Shapes:**
  - `A.shape == [B, N, N]`
  - `C.shape == [B, N, d]`
  - `output.shape == [B, N]`
- **Ranges / signs:**
  - `A >= 0` everywhere (softmax output is non-negative)
  - `loss >= 0` (if the loss is a norm or cross-entropy)
- **Normalization / conservation:**
  - `A.sum(over last axis) == 1` for every `(b, i)` (row-stochastic)
- **Monotonicity / limits / invariances** (when the math implies them):
  - permutation-equivariance, scale-invariance, a known limit
    (e.g. temperature → 0 ⇒ attention → argmax), etc.

Each invariant should be phrased so it can be checked numerically with a
tolerance on a small synthetic input. Prefer specific, mechanical claims
(the same "consequence list" discipline the Critic uses) over vague
ones. Do **not** list invariants you cannot justify from the math.

### 5. Cross-references

- [spec.md](spec.md) — the structured extraction this blueprint
  reconstructs.
- Concept files (`<concept>.md`) for the method, if any exist.
- Note explicitly: **no `code_map.md`** for this paper (no official
  code), or, if the user requested a blueprint despite official code
  existing, link `code_map.md` and state why both exist.

## Pre-emission Critic gate (hop-1 guard)

The blueprint is **not written to disk until it passes the Critic**.
This mirrors the tutor/explainer inline gate and the two-memory design
(`log/2026-06-02-...`): the Critic holds an **independent** reading of
the paper and audits the generator's draft.

Procedure (run by the Implementer, see `implementer.md`):

1. Draft the full blueprint **in working memory** (do not write the
   file yet).
2. Invoke the **Critic in blueprint mode** (`.cursor/agents/critic.md`),
   passing the **draft blueprint text as payload** (not a file path) and
   the `<slug>`. The Critic re-derives the paper's consequence list from
   `spec.md` / the PDF independently and checks the draft's §3 steps and
   §4 invariants against it.
3. **PASS** → write `code_blueprint.md` to
   `vault_path(slug, "code_blueprint.md")`.
4. **FAIL** → revise the draft per the Critic's findings and re-invoke.
   **Retry budget: max 2.** If still failing after 2 retries, **do not
   write the file**; surface the unresolved findings to the user and end
   the turn (escalate).

There is no write-then-rewrite loop: the file appears on disk only once,
already critic-approved.

## Self-checks (before invoking the gate)

- §2 defines every symbol used in §3 and §4.
- Every reducing/normalizing operation in §3 names its axis explicitly.
- §4 is non-empty and contains at least shape invariants for every named
  output, plus every normalization/sign/range property the math implies.
- No runnable code, no framework-specific calls anywhere.
- The "reconstructed, not official" disclaimer is present in the header.
- `⚠️ UNCERTAIN:` flags mark any quantity the spec/PDF could not pin.
