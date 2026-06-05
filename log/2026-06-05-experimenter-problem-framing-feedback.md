# 2026-06-05 — Experimenter feedback: problem-framing first; critic context audit

First real `/experimenter` smoke run (topic `GIB`, members `GIBGAT` +
`GIBSR`) surfaced an interaction-design gap and two fidelity-audit gaps.
This log records the user feedback, the audit of the generated artifacts,
and the fixes applied across the experimenter + critic prompts.

## User feedback (verbatim intent)

- It scanned the paper and asked **directly what to compare** — jumped to
  the comparison criterion. Never asked **what the experiment is for**
  (the task: node classification vs. graph prediction?) or **why** the
  paper's method is needed. "Totally miss the point."
- The experimenter suite's purpose is to **help the user design
  experiments** — understand the problem setup first.
- It should be an **interactive session**: pause, let the user read and
  think, not force multiple-choice answers.
- The design should be **led by the user**, not the agent.
- It does create files in the right places.
- **More weight on understanding the problem setup** than rushing to
  build the design.

## Faithfulness audit of the generated artifacts (read-only)

Artifacts: `vault/experiments/GIB/{design.md, comparison.md}`,
`sandbox/experiments/GIB/{scaffold.py, run.py, methods/*/extracted.py,
results/}`.

**Component-level extraction: faithful.**
- `methods/GIBGAT/extracted.py` reproduces `GATConv.message` sampling
  (categorical Gumbel-softmax, multi-categorical-sum, Bernoulli /
  RelaxedBernoulli with clamp + norm branch, both `AIB` KL estimators)
  matching `GIB_node_model.py:348–436`. Honest provenance header.
- `methods/GIBSR/extracted.py` reproduces `assignment()` + `aggregate()`
  + connectivity penalty from `gib_gin.py`, and **fixed** the upstream
  batch-contamination gotcha (per-graph slicing). Defensible.
- GIBSR MI critic + bi-level loop in `run.py` mirror `ours_train_eval.py`
  including the documented `pp_weight` loss-mix gotcha.

**Where the *experiment* drifted (the downstream symptom):**
1. `[CONTEXT-DRIFT]` — `run.py`'s `StructuralGATLayer` is a hand-rolled
   **single-head** GAT, not PyG multi-head `GATConv`. The sampling is
   extracted; the attention backbone it rides on is a silent
   simplification (critic gate only `[PROVENANCE-GAP]` WARN'd it).
2. `[INCOMPLETE-METHOD]` — GIBGAT's objective is `AIB` **+** `XIB`; the
   wired GAT path implements **only** `AIB`. Half the method's
   compression dropped, not flagged.
3. **Confounded comparison.** GAT+node-labels+mean-pool vs.
   GIN+graph-labels+subgraph-readout. The critic's own verdict called the
   scaffold "loose (shared data + eval only)" — i.e. the Stage-2
   component-surgery premise (one principle fixed, one slot swapped) did
   **not** hold for this pair. Result: ceiling effect (~1.0 acc across
   variants), H1–H3 inconclusive. The design honestly flags this five
   times in `⚠️ UNCERTAIN`, but only *after* the contrivance was built.

**Through-line:** GIBGAT is a *node*-classification robustness method;
GIBSR is a *graph*-classification/interpretation method. They don't share
a task. A problem-framing phase would likely have surfaced the mismatch
*before* code — reframing the question or repairing the pairing — instead
of baking in a node→graph bridge that measured noise.

## Fixes applied

### Experimenter (interaction design) — `ml-experiment-design/SKILL.md` + `experimenter.md`

- **New `design.md` §0.5 "Problem setup and motivation"** — the spine,
  settled *before* criterion: task/problem class, motivating question,
  why each method, and an explicit shared-task check.
- **R0 — Problem framing before design.** No spec deep-read, no
  criterion, no comparison axis until the problem is shared understanding.
- **R0a — Converse, don't railroad.** Open-ended questions; pause for the
  user to read/think; reserve multiple-choice for genuine forks; user
  leads.
- **R0b — Shared-task check (soft stop).** If methods don't share a task,
  stop and surface it; **recommend** reframing / swapping methods;
  proceed with a bridged design only on the user's explicit insistence,
  recording the confound in §0.5 + §7. Never bridge silently.
- **R2 reordered:** problem framing → criterion → methods → seam →
  hypotheses → data → MVP.
- `experimenter.md`: greeting now opens on *purpose/task*, not criterion;
  new **§2.0 Phase 0** loop step with the guardrails; seam step (§2e) and
  scope boundaries gain the shared-task check + anti-railroad rule.

### Critic (fidelity audit) — `ml-critique/SKILL.md` + `critic.md`

The extraction-fidelity mode audited only `extracted.py`, so it missed
the backbone swap and the dropped IB term (both live in `run.py`).

- **Audit surface widened to `run.py`**, not just the components.
- **New Check A1 — context faithfulness & completeness:** (a) backbone
  substitutions in `run.py` must be declared and behavior-preserving; (b)
  the method's **full** mechanism (all IB / reg / MI terms per
  spec/code_map) must be wired, or recorded as out-of-scope in
  `design.md`.
- **New FAIL tags:** `[CONTEXT-DRIFT]` and `[INCOMPLETE-METHOD]`, added to
  verdict rules + reporting in both skill and agent.

## Not changed (deliberately)

- Existing rule numbering kept (`§0.5`, `R0/R0a/R0b`) to avoid churn in
  the many references to `R1–R7` / `§2b` / `§4` across `coder.md`,
  `ml-experiment-code`, and `experimenter.md`.
- The `GIB` smoke-test artifacts were left in place (not regenerated);
  this pass fixes the *prompts*, not the one-off output.
