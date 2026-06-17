# 2026-06-17 — Evaluator subagent + experimenter Build-evaluate sub-phase (B+A protocol)

Built the `evaluator` subagent and the `ml-evaluation` skill, and wired
them into the `experimenter` via a new **Build-evaluate** sub-phase
plus a **filesystem-state-aware topic-detection** rule on entry.
Together these complete the experimenter suite's stop-line — until
today an experiment could only run to "results emitted"; now it runs
to an interpreted `findings.md`.

This log captures the design conversation (six questions and the
answers chosen), the **B+A multi-day-run protocol**, the file list,
the validation run, and a short list of schema follow-ups surfaced by
the validation.

## Design conversation — six questions

The design phase went through six questions in chat before any code
was written. Recording them here so the rationale is recoverable
without re-deriving it.

### Q1 — what is `findings.md` for?

Two valid framings: (a) a results write-up (prose, sections, narrative,
verdict against hypotheses); (b) a structured ledger (per-hypothesis
rows with metric, value, threshold, status). User picked **both** —
"make two sections, 1. results, 2. ledger." Schema honors this: section
2 is a `Hypothesis ledger` table; section 3 is `Results` (prose).

### Q2 — does the evaluator return PASS/FAIL to the experimenter?

User picked **no**. The user judges. The evaluator's ledger reports
`supported` / `not supported` / `inconclusive` per hypothesis; there is
no design-level verdict. Mirrors the asymmetry between the `critic`
(audits, returns PASS/FAIL on its gates) and the `evaluator`
(interprets, surfaces structured evidence, lets the user judge).

### Q3 — honesty discipline

Adopt the critic's `[A]` (paper-anchored) / `[B]` (reader-inferred)
tagging, plus a third tag `[E]` for empirically grounded by *this*
run. Mandatory in every section past the front-matter and Header. A
bare claim is a defect. Approved.

### Q4 — schema branching by `research_type` (six values)

Three options laid out: (a) one schema, prose adapts; (b) per-variant
section list; (hybrid) (a) backbone with (b) as a Results-section
runbook the agent picks based on `design.md`'s `research_type`. User
picked **hybrid** after the options were spelled out.

The skill encodes this: section names and order are fixed across all
research types; only the *body shape of the Results section* adapts.
Six runbooks (methods comparison / ablation / reproduction /
sensitivity / exploration / custom), each a 4–6 bullet checklist of
what tables / sub-sections to produce.

### Q5 — partial / smoke results

Two layers, composed:

- **Experimenter layer** — pause discipline. When results are missing
  or look like a smoke / dev run, the experimenter **pauses the chat**
  with a clear "run X, ping me / re-open later" instruction. It does
  not call the evaluator on empty results.
- **Evaluator layer** — permissive with flags. When invoked, it reads
  whatever's in the results directory and writes `findings.md`,
  tagging affected hypotheses `[INSUFFICIENT-RUN]` with ledger status
  `inconclusive`. Never refuses.

The two compose: in production the experimenter prevents premature
evaluation; if someone calls the evaluator anyway, it stays useful
and honest.

### Q6 — build scope

Three cuts: small (docs only), medium (docs + validation run),
medium-plus (docs + validation + experimenter wiring). User picked
medium and then asked to "add the wiring changes too" — medium-plus.

## B+A multi-day-run protocol

Real experiments take hours to days. A single `/experimenter` chat is
not a viable sleep medium. Three options were considered:

- **A — same chat, wait it out.** Realistic for minutes-to-hours.
- **B — end the chat after Build-implement emits the run command;
  resume later by re-running `/experimenter <topic>`.** The
  experimenter detects state from the filesystem and resumes:
  - No `design.md` → Plan phase (greenfield).
  - `design.md` exists, `run/results/` empty → Plan-resume /
    Build-implement-resume.
  - `design.md` exists, `run/results/` populated → propose
    **Build-evaluate**.
- **C — bypass the experimenter, add `/evaluate <topic>` direct
  command.** Rejected: breaks the design log's principle that the
  conversation always stays with the experimenter.

A and B are not in conflict — they are the same protocol with
different wait times. `design.md` is the durable handoff artifact
across sessions. The state-detection rule is the spine.

The experimenter skill now encodes this as
`# Topic state detection on entry` (runs before Plan turn 1) and a
new `## 3. Build-evaluate sub-phase` plus
`## Pause discipline (no premature evaluation)`. The old
`## 3. Stop boundary` (which carried the "evaluator not yet built"
caveat) is replaced.

## Files

### Created

- `.cursor/agents/evaluator.md` — backend-only agent contract;
  documents invocation (only by experimenter), inputs, process,
  output (one file: `findings.md`), `[A]`/`[B]`/`[E]` discipline,
  `[INSUFFICIENT-RUN]` flag rule, scope boundaries.
- `.cursor/skills/ml-evaluation/SKILL.md` — authoritative
  `findings.md` schema. Five fixed sections (Header, Hypothesis
  ledger, Results, Threats to validity, What the user can conclude),
  six variant runbooks for the Results section, tagging discipline,
  completeness check, self-check before returning.
- `log/2026-06-17-evaluator-build.md` (this file).

### Modified

- `.cursor/skills/experimenter/SKILL.md`:
  - Added `# Topic state detection on entry`.
  - Replaced `## 3. Stop boundary` with three new sub-sections:
    `## 3. Build-evaluate sub-phase`, `## Pause discipline`,
    `## Stop boundary` (now meaning "after `findings.md` is written").
  - Added `# Invoking the evaluator (Build-evaluate sub-phase)`.
  - Updated `# Reporting back` to include evaluator-side outcome.
  - Updated `# Scope boundaries` — removed "(when it exists)" from
    the evaluator mention.
- `AGENTS.md`:
  - Experimenter suite intro: `evaluator` "designed" → "shipped
    2026-06-17"; experimenter row gains B+A protocol summary +
    Build-evaluate sub-phase.
  - `evaluator` row rewritten to describe the shipped agent.
  - Agent-to-skill mapping: `ml-evaluation` "planned" → "shipped".
- `ROADMAP.md`:
  - Agents table `evaluator` row: Designed → Shipped 2026-06-17,
    full role description added.
  - Reference: backend subagents list now includes `evaluator`.
  - Reference: skills list now includes `ml-evaluation`.
  - Planned units §1: `evaluator` build-order entry updated;
    "next" reset to "full orchestration smoke + production-flow
    re-validation via `/experimenter` from a fresh chat".

## Validation run (Unit 3)

Validation followed scope choice **a** (use existing smoke results)
after a calibration miss on the original choice **b** (5-epoch
full-data run): per-epoch cost on the full 200-graph dataset is
~100 seconds, not the ~5 seconds the smoke run suggested, because
the forward pass has explicit Python loops over nodes / hops / heads
in `_structure_and_pool`. A 100-epoch / 2-seed run was
re-estimated at ~5–6 hours; even 3 epochs / 1 seed exceeded a
5-minute timeout. Two background runs were aborted; smoke was used
instead.

The evaluator subagent was invoked directly by the main chat agent
(option A1, mirroring the 2026-06-16 critic extension-fidelity
validation pattern) on
`sandbox/experiments/gib-importance/run/results/smoke_results.json`.
The resulting `findings.md` was written to
`<vault>/experiments/gib-importance/findings.md` (first-time write,
no regenerate prompt).

Outcome:

- All five fixed sections present and in order.
- All three hypotheses (H1, H2, H3 from `design.md` §3) ledgered as
  `inconclusive` with `[INSUFFICIENT-RUN]` in Notes.
- Results section follows the **exploration** runbook: per-H#
  presence sentences, walkthroughs, surprises block, threshold-
  distance table. Coherent prose; not formulaic.
- Every claim past the front-matter and Header carries `[A]`,
  `[B]`, or `[E]`.
- No PASS/FAIL synthesis.

The completeness check correctly classified the JSON as smoke
(`smoke: true`, 5 vs 2000 epochs, 10 vs 200 graphs, 1 vs 5 seeds);
the `[INSUFFICIENT-RUN]` flag fired everywhere it should.

## Schema follow-ups (surfaced by validation)

The evaluator's hand-off note flagged two minor ambiguities that
the schema could be tightened on. Recording here; not blocking.

1. **Gating hypotheses.** GIBGAT's H3 is *conditional*: "when
   accuracy < 0.75, recovery numbers are not interpretable as IB
   evidence." That is not a metric threshold; it is a
   meta-constraint on whether other hypotheses' numbers count. The
   `[INSUFFICIENT-RUN]` rule is written for "the run does not let
   you decide it" cases (smoke / missing seeds / missing metric);
   it does not explicitly cover *gating* hypotheses where the run
   may technically meet the gate's letter but not its spirit (e.g.
   accuracy 1.0 on 10 graphs after 5 epochs is "passing" but not
   "convergence-conditioned"). The evaluator flagged H3 by judgment.
   Skill could spell out a gating-hypothesis sub-rule.
2. **Table-cell tagging convention.** The Hypothesis ledger has
   `Observed` cells tagged `[E]` and `Status` / `Notes` cells
   untagged. The skill's tagging rule says every claim past the
   header is tagged; the table breaks this for cells that are
   structural rather than claim-bearing. Convention is consistent
   with the schema's intent but easy to misread as
   "every table cell must be tagged." Skill could call this out
   in a one-line note.

Neither is fixed in this commit. Both would be one-paragraph edits
to `ml-evaluation/SKILL.md`.

## Open follow-ups

1. **A2 — production-flow re-validation.** End-to-end the suite is
   now fire-able from a fresh `/experimenter gib-importance` chat
   (the production path):
   - Plan-resume picks up from existing `design.md`.
   - User runs the full 2000-epoch / 5-seed training (days,
     possibly).
   - User re-opens `/experimenter gib-importance`.
   - Filesystem-state detection sees `run/results/results.json`,
     proposes Build-evaluate.
   - User confirms; the experimenter invokes the evaluator legitimately;
     `findings.md` is overwritten via the regenerate prompt or
     replaced under the user's call.
   - Verifies the production hand-off + the B+A multi-day path.
2. **Schema follow-ups (above).** Worth a small Q-and-A and edit pass
   when the next non-exploration `research_type` exercises the
   schema (ablation, reproduction, or sensitivity will surface
   their own runbook ergonomics).
3. **Throughput.** GIBGAT's `_structure_and_pool` is the bottleneck
   — explicit Python loops do not vectorize. A vectorized
   reimplementation (sparse-matmul attention over hop pools) would
   bring the per-epoch cost down by ~10–50× and make full-spec runs
   tractable inside one chat session. Out of scope for the evaluator
   build; a separate Stage-1 cleanup task for GIBGAT.
4. **Stage-2 component-surgery exercise.** The evaluator has only
   been validated against an `exploration` run. The other five
   research-type runbooks (methods comparison, ablation,
   reproduction, sensitivity, custom) are unexercised. The natural
   first non-exploration test is a methods-comparison experiment
   between two papers in the vault — surfaces the runbook + the
   component-surgery + extraction-fidelity path.
