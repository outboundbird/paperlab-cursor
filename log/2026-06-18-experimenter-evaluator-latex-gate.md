# 2026-06-18 — Inline LaTeX gate for experimenter and evaluator (no citation gate)

Closes Gaps 1, 2, and 3 from
[`log/2026-06-17-evaluator-experimenter-gaps.md`](./2026-06-17-evaluator-experimenter-gaps.md)
with a partial Option-A: add an inline **LaTeX** gate to the
`evaluator` (`findings.md`) and confirm/keep the inline LaTeX gate
on the `experimenter` (`design.md`); **drop** the citation gate
from both. The `comparator` (`comparison.md`) keeps both gates
unchanged.

## Decision

Asymmetric coverage on the `experiments/<topic>/` tree:

| Artifact | Writer | LaTeX gate | Citation gate |
|---|---|---|---|
| `comparison.md` | `comparator` | inline | inline |
| `design.md` | `experimenter` | inline | **none (was inline → removed)** |
| `findings.md` | `evaluator` | **inline (added today)** | none |

The post-hoc verifier hook skips this entire tree (multi-paper
files have no single `<slug>` folder), so the inline gate is the
sole verification path for each writer.

## Rationale

`design.md` and `findings.md` compose material from upstream agents
whose external citations are already gated:

- `spec.md` — LaTeX-gated by the dissector + post-hoc hook covers citations.
- `comparison.md` — inline LaTeX + citation gate (comparator).
- `code_map.md`, `critic_reviews.md`, `code_review.md` — post-hoc
  hooked.

Novel external citations *introduced inside* `design.md` or
`findings.md` themselves are rare in practice. `design.md` is
constructed conversationally with the user before write, so any
external reference passes through the user's eyes; `findings.md` is
anchored in run-output JSON, not literature.

The LaTeX surface, by contrast, is non-trivial in both files —
metric formulas, hypothesis math, restated equations from the paper
— exactly the lexer's reason for existing. LaTeX gate stays.

## Alternatives considered

- **Full Option A (LaTeX + citations on both files).** Recommended in
  the gaps log. Rejected because the citation cost is real (network
  calls, retry budget, occasional false-mismatch noise from the
  resolver) for a low-risk surface in this specific tree.
- **Option B (document the omission, no gates added).** The
  experimenter already had an inline LaTeX + citation gate baked in
  via `ml-experiment-design`. Pure-B would have removed both;
  instead we kept LaTeX on `design.md` (already shipped, no extra
  cost) and added LaTeX to `findings.md` (one new section).

## Revisit trigger

Add a citation gate to the offending writer if a hallucinated
arXiv ID, DOI, URL, or mismatched citation metadata is observed in
`design.md` or `findings.md` in practice. Cost: one section in the
relevant skill, copy-paste from `ml-comparison/SKILL.md`'s R11.

## Files touched

Edited:

- `.cursor/skills/ml-experiment-design/SKILL.md` — "Verification gate"
  section: removed step 2 (citation gate); kept LaTeX gate; added
  rationale paragraph + revisit pointer to `AGENTS.md`. Self-checks
  updated.
- `.cursor/skills/experimenter/SKILL.md` — Build phase step 5
  (verification gate invocation): now LaTeX-only with explicit "no
  citation gate" note; "Reporting back" gate-outcome line updated.
- `.cursor/skills/ml-evaluation/SKILL.md` — Process: new step 8
  ("Inline LaTeX verification gate") between regenerate-prompt and
  return; old step 8 (Return) renumbered to step 9 with the gate
  outcome added to the return summary; self-check entry added.
- `AGENTS.md` § Verifier system — inline-gate paragraph now lists
  `experimenter` and `evaluator` (LaTeX only); post-hoc hook
  paragraph updated to point at the new asymmetry section; new
  subsection "Asymmetry on the experiments tree (LaTeX yes,
  citations no for `design.md` / `findings.md`)" with the table,
  rationale, and revisit trigger.
- `ROADMAP.md` — `experimenter` and `evaluator` agent-table rows
  updated with the 2026-06-18 LaTeX-gate addition; new entry under
  Known limitations: "No citation gate on `design.md` / `findings.md`".

Created:

- `log/2026-06-18-experimenter-evaluator-latex-gate.md` (this file).

## Status of yesterday's gaps

- **Gap 1 (no verifier gate on `findings.md`)** — *closed*: LaTeX
  gate added; citation gate deliberately omitted with documented
  rationale.
- **Gap 2 (`AGENTS.md` § Verifier system silent on the evaluator)** —
  *closed*: section now lists evaluator alongside comparator (LaTeX
  only) and explains the asymmetry.
- **Gap 3 (`design.md` had no gate)** — *partially pre-closed,
  finalized today*: `ml-experiment-design` already had an inline
  LaTeX + citation gate; removed the citation half today to match
  the evaluator's posture and the table above.
- **Gap 4 (schema follow-ups: gating hypotheses, table-cell tagging)**
  — **not addressed today.** Still open; recommended as the next
  cheap win.

## Next step (unchanged from yesterday)

A2 — production-flow re-validation of the full `/experimenter` loop
from a fresh chat on the `gib-importance` topic. See
`log/2026-06-17-gibgat-extension-regime-revalidation.md` § Open
follow-ups #1.
