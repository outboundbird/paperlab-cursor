# 2026-06-17 — Gaps surfaced by the evaluator-ship review

After today's evaluator + Build-evaluate sub-phase ship (see
[`2026-06-17-evaluator-build.md`](./2026-06-17-evaluator-build.md)),
a review pass over the seven commits surfaced four gaps worth
addressing in a follow-up build session. Recording them here so the
context is recoverable without re-deriving it.

## Gap 1 — No verifier gate on `findings.md`

**What.** The post-hoc verifier hook (`tools/hooks/verify_on_vault_write.py`)
explicitly skips the `experiments/<topic>/` tree (per `AGENTS.md`
§ Verifier system: "multi-paper files have no single `<slug>` and are
gated inline by the comparator"). The `comparator` compensates by
running an **inline** LaTeX + citation gate before emission. The
`evaluator` does not — but `findings.md` carries:

- LaTeX (metric definitions, equations restated from the paper).
- `[A]`-tagged paper-anchored claims that, in principle, should
  resolve to the cited paper.

So the same failure modes the inline gate exists for (broken math
blocks, hallucinated arXiv IDs, mismatched citation metadata) can
land in `findings.md` unverified.

**Symmetric to.** The `comparator`'s situation circa 2026-05-29 —
same tree, same hook skip, same call to wire an inline gate.

**Decision needed.** Either:

- **Add an inline LaTeX + citation gate** to
  `.cursor/skills/ml-evaluation/SKILL.md` (mirror the comparator's
  R10/R11 — fix → retry ×2 → disclose, separate budgets), invoked
  pre-emission inside the evaluator's process loop.
- **Or document the deliberate omission** with rationale (e.g.,
  "evaluator does not introduce new citations; `[A]` tags resolve
  to paper-internal references already verified upstream").

Recommendation: **add the gate.** Cost is low (one section in the
skill + a process step), and the evaluator does restate equations
from the paper — exactly the surface the LaTeX verifier exists for.
Citations are thinner but non-zero (the `[A]` discipline can pull in
external citations from `design.md`'s References).

## Gap 2 — `AGENTS.md` § Verifier system is silent on the evaluator

**What.** The Verifier system section enumerates inline gates for
`tutor`, `explainer`, `dissector`, `comparator` and the post-hoc
hook for "any agent other than `tutor` or `explainer-intermediate`."
The `evaluator` now exists and falls outside both regimes (writes
into `experiments/`, hook skips it, no inline gate today).

**Decision needed.** Tied to Gap 1's resolution:

- If we add the inline gate (Gap 1), update the section to list the
  evaluator alongside the comparator under inline-gated agents.
- If we omit, document the omission and the rationale here so a
  future reader doesn't re-discover the gap as a bug.

**Cost.** One paragraph either way.

## Gap 3 — `design.md` has the same hook-skip / no-gate condition

**What.** The `experimenter` writes `design.md` into
`experiments/<topic>/`. The hook skips this tree. The experimenter
skill has no inline LaTeX / citation gate. Same shape as Gap 1, for
the design artifact rather than the findings artifact.

**Pre-existing.** Not introduced today. But the experimenter skill
**was** touched today (Build-evaluate sub-phase, B+A protocol), so
it is natural to address now or note explicitly that this is a
known unchecked surface.

**Note.** `design.md` carries hypotheses, metric formulas, and a
References section — the same surfaces the verifiers exist for.
Arguably more important to gate than `findings.md` since `design.md`
is the durable, multi-day handoff artifact (B+A protocol).

**Decision needed.** Same as Gap 1 — add inline gate to
`.cursor/skills/experimenter/SKILL.md` (Build-implement phase,
before the `design.md` write step) or document the omission.

## Gap 4 — Schema follow-ups from validation aren't on the roadmap

**What.** The validation run (Unit 3 of today's evaluator build)
surfaced two ambiguities in `ml-evaluation/SKILL.md`:

1. **Gating hypotheses.** A hypothesis whose interpretability is
   *conditional* on another (GIBGAT's H3: "if accuracy < 0.75,
   recovery numbers don't count as IB evidence") is not covered by
   the existing `[INSUFFICIENT-RUN]` rule. The skill could spell
   out a gating-hypothesis sub-rule.
2. **Table-cell tagging convention.** The skill's tagging rule
   ("every claim past the header carries `[A]`/`[B]`/`[E]`") is
   inconsistent with the Hypothesis ledger's `Status` and `Notes`
   cells, which are structural rather than claim-bearing. A
   one-line note in the skill would resolve.

Both are documented in `2026-06-17-evaluator-build.md`
§ "Schema follow-ups" but **not** in `ROADMAP.md`
§ "Schema improvement candidates," so they will be invisible to a
future skim.

**Decision needed.** Two micro-edits:

- Add a "Gating hypotheses" sub-rule to the
  `[INSUFFICIENT-RUN]` section of `ml-evaluation/SKILL.md`.
- Add a one-line note on table-cell tagging convention to the
  same skill.
- Surface both as entries under `ROADMAP.md` § Schema improvement
  candidates with a back-link to today's build log.

**Cost.** ~10 lines of edits; trivial.

## Suggested build order for tomorrow

By cost ascending and visibility descending:

1. **Gap 4** (schema follow-ups + roadmap surface) — cheapest,
   highest visibility win, no design call.
2. **Gap 2** (`AGENTS.md` verifier-system update) — one paragraph,
   but tied to Gap 1's outcome, so do it after Gap 1 settles.
3. **Gaps 1 + 3 together** (inline gates for `findings.md` and
   `design.md`) — the real design call. Same template (mirror the
   comparator), same skill-edit shape, same cost; doing both at
   once avoids a half-finished verification posture.

If energy is short, **Gap 4 alone** is a clean stopping point and
unblocks future skims of the roadmap.

## Items checked clean today (for the record)

- `findings.md` front-matter uses the multi-paper variant
  (`topic:` + `papers:` list) correctly.
- All four concepts referenced in `findings.md`
  (`information-bottleneck`, `graph-classification`, `attribution`,
  `graph-attention-network`) already present in
  `.cursor/skills/concept-vocabulary.md`.
- `AGENTS.md` Experimenter-suite paragraph, agent table row,
  agent-to-skill mapping, and Reference list all updated for the
  evaluator + B+A protocol.
- `ROADMAP.md` agent row, build-order entry, "what's currently
  working" subagent + skill lists all updated.
- `ml-evaluation/SKILL.md` correctly invokes the
  `paperlab-regenerate-prompt` rule (line 18 + process step 7).
- `paperlab-regenerate-prompt.mdc` covers the `evaluator` via the
  "any future agent" wildcard — no rule edit needed.
- `.gitignore` scoping replaced the blanket
  `sandbox/experiments/*` exclusion with targeted ignores for
  generated `data/`, `run/results/*` (except `.gitkeep`), and
  `run_log.txt`. Code + seed config tracked, matching `AGENTS.md`
  convention.
- gib-importance Stage-2 extension regime code committed cleanly
  (7 files, 1168 insertions); `git status` clean at end of session.
