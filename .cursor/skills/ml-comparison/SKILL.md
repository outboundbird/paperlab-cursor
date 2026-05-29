---
name: ml-comparison
description: Defines the `comparison.md` schema for conceptual comparison of methods from multiple ML papers along a user-chosen axis. `comparison.md` lives at `vault_experiments_dir(topic)/comparison.md`. Use when comparing, contrasting, or relating the methods of two or more papers on a shared problem.
---

# ML Comparison Schema

## Purpose

This file defines the schema for `comparison.md`, a **conceptual**
comparison of the methods from two or more ML papers along a single
user-chosen **axis** (a property, objective, or design dimension the
methods can be lined up against). `comparison.md` is produced by the
Comparator subagent and lives at
`vault_experiments_dir(topic)/comparison.md` (resolved via
`tools/paths.py`).

The comparison is **conceptual**, not empirical — it reasons about how
each method addresses the axis from the papers' own descriptions. It
does **not** run code or interpret experimental results; that is the
`evaluator`'s job. When an experiment exists, the empirical comparison
goes in `findings.md`, written by the `evaluator` / `experimenter`.

A comparison spans multiple papers, so — unlike per-paper vault files —
it lives under `<vault>/experiments/<topic>/`, keyed by a user-chosen
`<topic>`, not under any single `<slug>/` folder.

## Scope: conceptual vs. empirical

| | This skill (`comparator`) | Out of scope (→ `evaluator`) |
|---|---|---|
| Source | `spec.md`, `code_map.md`, PDFs, vault notes | experiment run outputs (metrics, logs) |
| Question | how does each method *approach* the axis? | which method *won* the experiment, by how much? |
| Output | prose + conceptual tables in `comparison.md` | numbers in `findings.md` |

If the user asks "which is empirically better," the Comparator answers
only what the papers *claim* (flagged as claims), and notes that an
empirical answer requires the experimenter/evaluator.

## Sources

In priority order — prefer the cheapest sufficient source, escalate
only when it is insufficient:

1. **`spec.md`** for each paper (`vault_path(slug, "spec.md")`) — the
   primary source. Most comparisons can be built from specs alone.
2. **`code_map.md`** when present (`vault_path(slug, "code_map.md")`) —
   for design details the spec abstracts away.
3. **Paper text** via `tools.pdf.extract_pdf_text(slug)`, which returns
   the cached visible copy at `papers/<slug>/<slug>.txt` (extracting
   once if absent). Consult the PDF only when the spec is insufficient
   for the axis — do **not** re-derive the dissector's extraction.
4. **Other vault notes** (`<concept>.md`, `tutor_notes.md`, ...) when
   they clarify a method.

Always read each paper's `spec.md` first. If a paper in the requested
set has no `spec.md`, the Comparator cannot fairly include it — see the
agent's prerequisite handling.

## Conventions

- **Audience:** a reader who has read each paper's `spec.md`. Assume
  familiarity with each method individually; the comparison's value is
  in the *relation* between them.
- **Posture:** annotator, not judge. Surface how the methods differ and
  what each buys/costs. Do **not** crown a winner on conceptual grounds;
  "better" is an empirical question for the evaluator, or a claim
  attributable to a paper.
- **Notation across papers:** different papers use different symbols for
  the same object. Introduce a **notation-reconciliation table** (§3) and
  use one consistent symbol set in the comparison prose, noting each
  paper's original symbol once. Never silently conflate two papers'
  symbols that mean different things.
- **Inference-type discipline** (carried from `ml-critique`): when
  extending beyond what a paper states, prefix the inference:
  - `[A] Mechanical:` — a consequence that follows from a stated
    property by the paper's own framework.
  - `[B] Scope:` — an observation about what a method covers or doesn't,
    where the reference point is named in the paper itself.
  - **Forbidden:** `[C]` field-level critique — do not rank or fault a
    method based on general field knowledge or work a paper does not
    reference. Cross-paper comparison is exactly where `[C]` creeps in;
    keep every comparative claim anchored to a source.
- **Math notation:** LaTeX between `$ ... $` (inline) and `$$ ... $$`
  (display). Never Unicode math; never `\( ... \)` or `\[ ... \]`.
- **Citations:** when referencing a paper's external claim with an
  arXiv ID / DOI / URL, format it so the citation verifier can resolve
  it. Bare author-year mentions are fine but unresolvable (out of scope
  for the verifier).
- **Length target:** 2–4 pages. Scales with the number of methods.

## LaTeX + citation verification (inline gate)

`comparison.md` is math- and citation-dense, so the Comparator verifies
its output **inline**, before declaring the comparison complete — it is a
gated agent, **not** a post-hoc-only one. It is the first agent to gate
*both* LaTeX and citations inline: the Tutor and Explainer gate both
inline on draft text, while the Dissector gates only LaTeX inline and
leaves citations to the post-hoc hook. The Comparator gates both because
the post-hoc hook deliberately skips the `experiments/` tree (the hook
assumes a per-paper `<slug>/` folder, which does not fit the multi-paper
`experiments/<topic>/` layout), so the inline gate is the comparator's
sole verification path.

The gate runs **LaTeX first, then citations**, each with its own retry
budget (max 2). After writing `comparison.md`:

1. **LaTeX gate.** Invoke the `latex-verifier` in **Mode A** (file on
   disk) on the resolved `comparison.md` path.
   - **PASS** (no error-severity findings) → proceed to the citation
     gate. Warnings do not block.
   - **FAIL** → fix each named error, rewrite, re-verify. Retry budget
     max 2. If still failing, **disclose** the remaining errors in the
     report rather than emitting silently.
2. **Citation gate.** Invoke the `citation-verifier` in **Mode A** on the
   same file. It requires a `--slug` for the per-paper resolver cache;
   pass the **first compared slug** (the cache is just resolver
   memoization — any compared slug is a valid key).
   - **PASS** (no `mismatched` rows) → done. `unresolved` rows are
     warnings: surface them in a short disclosure but do not block (a
     transient resolver issue commonly affects valid citations).
   - **FAIL** (1+ `mismatched`) → fix each mismatch, rewrite, re-verify.
     Retry budget max 2. If still failing, disclose the remaining
     mismatches.

Only after both gates pass (or their budgets are exhausted with
disclosure) does the comparator report the comparison complete.

## Required sections (in this order)

### 0. Header

Every `comparison.md` begins with this header. Note the multi-paper
front-matter: `topic:` + `papers:` (a list), **not** the singular
`paper:` used by per-paper files.

```markdown
---
topic: <topic>
papers:
- <slug_a>
- <slug_b>
- <slug_c>
category: comparison
agent: comparator
tags:
- AI-guided-paper-reading
- method-comparison
---

# Comparison — <topic>

**Axis:** one-sentence statement of the dimension being compared
**Methods:** <slug_a>, <slug_b>, <slug_c>
**Sources:** spec.md (all), code_map.md (where present), PDF (where consulted)
**Date:** MM/DD/YYYY

---
```

If a slug contains a YAML-special character, quote it (see `AGENTS.md`
front-matter rules).

### 1. Axis

Restate, precisely, the dimension being compared and why it is a fair
basis for lining these methods up. If the user's axis was refined during
the session (sharpened, split, or a coverage gap noted), record the
final agreed axis here, and note the refinement in one sentence.

If the axis is only partially comparable (some methods do not address
it), state that here and carry it into §5 rather than forcing a false
equivalence.

### 2. Per-method summary

One block per paper. Summarize how *this* method addresses the axis, in
the method's own terms, cited to its `spec.md`. Keep each block
self-contained; the comparison itself comes later.

**<slug_a>** — *(spec.md §X)*
- **Approach to the axis:** how this method engages the compared dimension.
- **Key mechanism:** the one or two ideas that do the work, with the
  paper's notation.
- **Stated scope:** what the paper claims this approach covers.

Repeat for each method.

### 3. Notation reconciliation

A table mapping each paper's symbol for shared objects to one common
symbol used in this document. Only include objects that appear in more
than one paper (or that the comparison prose references).

| Common symbol | Meaning | <slug_a> | <slug_b> | <slug_c> |
|---|---|---|---|---|
| $\mathcal{G}$ | input graph | $G$ | $\mathcal{G}$ | $g$ |
| $z$ | learned representation | $h$ | $z$ | $r$ |

If a symbol exists in one paper but has no counterpart in another, write
`—` in that column.

### 4. Comparison table

A table with one row per method and one column per sub-dimension of the
axis. Columns are derived from the axis (e.g., for "OOD generalization
objective": *what is optimized*, *invariance assumption*, *failure mode
addressed*, *supervision required*). Keep cells terse; prose nuance goes
in §5.

| Method | <dimension 1> | <dimension 2> | <dimension 3> |
|---|---|---|---|
| <slug_a> | ... | ... | ... |
| <slug_b> | ... | ... | ... |

### 5. Key differences

Prose. Where do the methods genuinely diverge, and *why* — trace each
divergence to a design choice in the source. This is the analytical core
of the document. Use `[A]` / `[B]` prefixes when reasoning beyond what a
paper states. Call out any axis dimension where the methods are **not**
comparable, rather than papering over it.

### 6. Trade-offs

What each method *buys* and what it *costs*, framed around when a
practitioner would prefer one over another. This answers the user's
"what are the advantages of each method" directly. Attribute empirical
superiority claims to their source paper; do not assert them as fact.

- **<slug_a>:** buys [...]; costs [...]; prefer when [...].
- **<slug_b>:** buys [...]; costs [...]; prefer when [...].

### 7. Cross-references

Links to each source, plus any related vault concept files.

**Specs:**
- [<slug_a> spec.md](../../<slug_a>/spec.md)
- [<slug_b> spec.md](../../<slug_b>/spec.md)

**Related concepts** (if any): plain markdown links to `<concept>.md`
files in the vault.

> Note: cross-references from an `experiments/<topic>/` file to a
> per-paper `<slug>/` file are relative (`../../<slug>/spec.md`). The
> bidirectional-link rule that governs Tutor `<concept>.md` files does
> **not** apply here — the Comparator maintains one-way links only.

### 8. Uncertainty flags

A bullet list of every `⚠️ UNCERTAIN:` raised while building the
comparison (a method's approach to the axis was unclear from its
sources, an axis dimension was only partially comparable, a paper's
notation was ambiguous, ...). If none: "No uncertainty flags."

## Self-checks

Before reporting the comparison complete:

- Every requested paper has a §2 block, or is explicitly excluded (with
  reason) for lacking a `spec.md`.
- §3 reconciles every shared symbol used in the prose; no two papers'
  symbols are silently merged.
- No `[C]` field-level critique anywhere. Search for `[C]`; expect none.
- No method is declared the conceptual "winner"; superiority statements
  are attributed to a source or framed as empirical-and-deferred.
- The axis in §1 matches the `**Axis:**` header line.
- File written to `vault_experiments_dir(topic)/comparison.md`.
