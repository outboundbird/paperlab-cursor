# 2026-06-18 — Evaluator schema follow-ups (Gap 4)

Closes Gap 4 from
[`log/2026-06-17-evaluator-experimenter-gaps.md`](./2026-06-17-evaluator-experimenter-gaps.md).
Two micro-edits to `ml-evaluation/SKILL.md` plus a roadmap surface,
recording two schema clarifications surfaced by the GIBGAT
validation run during the evaluator build (2026-06-17).

## What was unclear

Both surfaced during yesterday's evaluator validation:

1. **Gating hypotheses.** GIBGAT's H3 ("recovery quality indicates IB
   compression") is interpretable only if H1 ("test accuracy ≥
   threshold") holds. The existing `[INSUFFICIENT-RUN]` rule did not
   cover this case — the run was spec-compliant; the chain of
   inference was broken upstream. The evaluator had no clear
   instruction for what status / flag to assign.
2. **Table-cell tagging convention.** The "every claim past the
   header carries `[A]`/`[B]`/`[E]`" rule was unclear about whether
   it applied to structural ledger cells (`Status` is a controlled
   vocabulary; `Notes` carries flags). Tagging them with `[E]`
   produced visual noise and confused readers about which cells
   carried claims.

## Decisions

### Gating hypotheses → new `[GATED-OFF]` flag (option a)

Distinct flag, not a sub-reason of `[INSUFFICIENT-RUN]`. Rationale:
the gaps log argued that gating is *not* an under-spec case (the
run is fine; the chain breaks upstream). A separate flag keeps the
threats-to-validity narrative honest — the user reads
"`[GATED-OFF]: depends on H1, which is not supported`" and knows
the gated number cannot be re-evaluated by re-running, only by
re-designing the experiment.

Behavior:

- Gated hypothesis status becomes `inconclusive` when the gating
  hypothesis is `not supported` or `inconclusive`.
- Chains transitively: if H3 is gated by H2, and H2 is `inconclusive`
  via `[GATED-OFF]: depends on H1`, then H3 inherits with
  `[GATED-OFF]: depends on H2, which is inconclusive`.
- The gated row's `Observed` cell still reports the run's number
  (`[E]`-tagged) for transparency, but the Results / conclusions
  sections do not read it as evidence.

### Structural-cell exception to the tagging rule

The `[A]`/`[B]`/`[E]` rule applies to *claim-bearing* prose and
numerical cells. Ledger `Status` and `Notes` are structural
(controlled vocabulary + flags), not claims. Explicit exception
added so future evaluators don't mechanically `[E]`-tag everything.

The `Observed` cell is still `[E]`-tagged by construction (it
*is* a numerical claim from the run).

## Files touched

Edited:

- `.cursor/skills/ml-evaluation/SKILL.md`:
  - Front-matter `description` updated to mention `[GATED-OFF]` and
    the structural-cell exception.
  - § Inference discipline: new "Structural cells" paragraph noting
    the exception for ledger `Status` / `Notes`.
  - § `[INSUFFICIENT-RUN]` flag rule: new sub-section
    "### Gating hypotheses ([GATED-OFF])" defining the flag, the
    status-mapping rules, the chain behavior, and the reporting
    behavior across ledger / threats / results / conclusions.
  - § Self-check before returning: new bullet checking that every
    `[GATED-OFF]` flag names a valid upstream hypothesis whose
    status is consistent with the gated row's status.
- `ROADMAP.md` § Schema improvement candidates: two new entries
  (gating-hypothesis rule, table-cell tagging convention) marked
  **shipped 2026-06-18** with back-links here and to yesterday's
  gaps log.

Created:

- `log/2026-06-18-evaluator-schema-followups.md` (this file).

## Status of the four gaps

After today's two commits (Gaps 1+3 closed earlier today, Gap 4
closed now):

- **Gap 1** — closed (LaTeX gate added to evaluator).
- **Gap 2** — closed (verifier-system section updated).
- **Gap 3** — closed (citation gate dropped from experimenter; LaTeX
  kept).
- **Gap 4** — closed (this commit).

All four gaps from `2026-06-17-evaluator-experimenter-gaps.md` are
now closed.

## Next step (unchanged)

A2 — production-flow re-validation of the full `/experimenter` loop
from a fresh chat on the `gib-importance` topic. See
`log/2026-06-17-gibgat-extension-regime-revalidation.md` § Open
follow-ups #1.
