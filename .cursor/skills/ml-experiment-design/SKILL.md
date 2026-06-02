---
name: ml-experiment-design
description: Defines the `design.md` and `findings.md` schemas for multi-paper empirical experiments, and the experimenter's interactive design-phase protocol. Files live at `vault_experiments_dir(topic)/`. Use when designing, scoping, or running an experiment that compares methods from multiple papers on synthetic data.
---

# ml-experiment-design

Authoritative schema and interaction protocol for the **experimenter**
subagent's design phase. The experimenter helps the user **design, run,
and interpret empirical experiments that compare methods from multiple
papers** on data tailored to a chosen criterion.

This skill covers the **design phase** (the experimenter's current,
shipped scope) and documents the `findings.md` schema for the
**evaluate phase** (write-path pending the `evaluator` agent — see
"Lifecycle and current scope").

## Where files live

Resolve via `tools/paths.py` — never hard-code:

- `vault_experiments_dir(topic)/design.md` — experiment design (this
  skill, design phase). Written by the experimenter.
- `vault_experiments_dir(topic)/findings.md` — results write-up
  (evaluate phase). Schema defined below; written by the experimenter
  from the `evaluator`'s output **once the evaluator exists**.
- `vault_experiments_dir(topic)/comparison.md` — conceptual comparison,
  written by the `comparator` (its own skill, `ml-comparison`).
- `repo_experiments_dir(topic)/` — code and data (the `coder`'s
  territory: `synth/`, `methods/`, `run/`, `results/`, git-ignored
  `data/`).

`<topic>` is **user-chosen** (a problem class, not a paper slug). The
slug rule applies: use it verbatim; if it is not a valid path segment,
ask for an alternative.

## Lifecycle and current scope

The full experiment lifecycle is **design → implement → run → evaluate**:

1. **Design** (experimenter ⇄ user) — **shipped.** Establish topic,
   criterion, method set, and data-synthesis design; write `design.md`.
2. **Method trade-offs** (on demand, design phase) — **shipped.**
   Invoke the `comparator` for a conceptual comparison; relay to user.
3. **Implement + run** — **pending** the `coder` agent. The experimenter
   will invoke the `coder` to scaffold synth + method code, with a
   user-check gate (Seam B) between writing and running.
4. **Evaluate** — **pending** the `evaluator` agent. The experimenter
   will invoke the `evaluator` to interpret run outputs and write
   `findings.md`.

Until the `coder` and `evaluator` ship, the experimenter completes the
design phase and **stops at the implement boundary**, telling the user
those phases are not yet available. It does not write code, run
experiments, or write `findings.md`.

## Seams (ownership boundaries)

- **Seam A — data design vs. data code.** The *data-synthesis design
  decision* (what distribution, what stresses the criterion, synthetic
  vs. small real, metrics/baselines/seeds) stays with the experimenter
  ⇄ user and is recorded in `design.md` §4. The `coder` *implements*
  this design; it does not decide it.
- **Seam B — user-check gate.** Between `coder`-writes-code and
  `coder`-runs-it, the user reviews the code. (Relevant once the `coder`
  ships; noted here so the design phase sets it up.)

## `design.md` — required sections (in this order)

### 0. Header

```markdown
---
topic: <topic>
papers:
- <slug_a>
- <slug_b>
- <slug_c>
category: experiment
agent: experimenter
status: designed
sources:
- "[[<slug_a>/spec.md]]"
- "[[<slug_b>/spec.md]]"
concepts:
- "[[<canonical-concept-name>]]"
tags:
- AI-guided-paper-reading
- experiment-design
---

# Experiment design — <topic>

**Criterion:** one-sentence statement of the property being tested
**Methods:** <slug_a>, <slug_b>, <slug_c>
**Date:** MM/DD/YYYY

---
```

`status: designed` is the experiment-suite lifecycle value for a
completed design (distinct from the per-paper pipeline). Quote any
YAML-special slug (see `AGENTS.md` front-matter rules).

### 1. Question and criterion

State the empirical question precisely: *what property* of the methods
is being tested (e.g. expressivity, sample efficiency, robustness to
distribution shift), and *why it matters* for this problem class. One
paragraph. This is the spine of the whole design — every later choice
serves it.

### 2. Methods under comparison

One short subsection per method (one per paper slug). For each: the
method name, the paper it comes from, and a one-to-two-sentence
statement of how it approaches the problem class. Keep it factual and
sourced from each paper's `spec.md`; deep conceptual contrast belongs in
`comparison.md` (invoke the `comparator`), not here.

If a `comparison.md` already exists for this topic, cross-reference it
with a `[[wiki-link]]` rather than restating its content.

### 3. Hypotheses

The expected outcome(s), stated as falsifiable predictions tied to the
criterion (§1). Each hypothesis names which method(s) it concerns and
what result would confirm or refute it. Mark predictions the papers
themselves make as `[A]` (author-stated) vs. your own inference `[B]`
(reader-inferred), mirroring the critic/comparator inference discipline.
Do not crown a winner here — these are predictions, not conclusions.

### 4. Data-synthesis design (Seam A — owned here)

The data plan. This is the experimenter's decision, recorded for the
`coder` to implement:

- **Generative process** — what distribution / structure the synthetic
  data has, and how it is parameterized.
- **Stress lever** — the knob that stresses the criterion (size,
  density, noise level, distribution-shift magnitude, ...). What is
  varied and over what range.
- **Synthetic vs. small real** — which, and why.
- **Pinned seed** — the design commits to a seed so data is regenerable
  (data itself is git-ignored; see file layout).

### 5. Minimum viable comparison

The smallest experiment that answers §1 honestly:

- **Metrics** — what is measured, and how each maps to the criterion.
- **Baselines** — what the methods are compared against (including any
  trivial baseline).
- **Seeds / repetitions** — how many runs, to gauge variance.
- **What is deliberately out of scope** — to keep the experiment small.

### 6. Decision rationale

Why these choices over alternatives. Capture the trade-offs discussed
with the user so the design is self-explaining on re-read. This is the
analogue of the design log's decision record, scoped to one experiment.

### 7. Uncertainty flags

Anything ambiguous or unresolved, each prefixed `⚠️ UNCERTAIN:`
(per `AGENTS.md`). Examples: a criterion that is hard to operationalize,
a method whose `spec.md` is too thin to implement faithfully, a data
design that may not isolate the property cleanly.

## `findings.md` — schema (write-path pending `evaluator`)

Documented now so the schema is stable; the experimenter writes this
from the `evaluator`'s output **once the evaluator ships**. Until then,
do not create this file.

### 0. Header

```markdown
---
topic: <topic>
papers:
- <slug_a>
- <slug_b>
category: experiment
agent: experimenter
status: evaluated
sources:
- "[[experiments/<topic>/design.md]]"
concepts:
- "[[<canonical-concept-name>]]"
tags:
- AI-guided-paper-reading
- experiment-findings
---

# Findings — <topic>
```

### Sections

1. **Result summary** — what happened, against each hypothesis (§3 of
   `design.md`): confirmed / refuted / inconclusive, with the numbers.
2. **Per-metric results** — tables/figures the `evaluator` produced.
3. **Interpretation** — what the results mean for the criterion. Attribute
   empirical superiority to measured outcomes (this is where a "winner"
   may be named, on empirical grounds — unlike `comparison.md`).
4. **Threats to validity** — seeds, variance, design limitations from
   `design.md` §5/§7 that bear on the conclusion.
5. **Uncertainty flags** — `⚠️ UNCERTAIN:` as needed.

## Interaction protocol (design phase)

The experimenter is **conversational and user-driven**, in the style of
the `tutor` — a pair-designer, not a fire-and-forget scaffolder.

- **R1 — User drives.** The user sets the topic and criterion. The
  experimenter proposes, surfaces trade-offs, and asks; it does not
  unilaterally fix the design.
- **R2 — One decision at a time.** Walk the design sections in order
  (criterion → methods → hypotheses → data → MVP). Do not dump a full
  design and ask for blanket approval; build it collaboratively.
- **R3 — Propose-and-confirm for vague inputs.** If the criterion is
  vague or not cleanly testable, propose a sharpened version and let the
  user confirm or adjust. Never silently substitute.
- **R4 — Trade-offs via the `comparator`.** When the user asks about the
  conceptual advantages of each method, invoke the `comparator` (backend
  mode) rather than reasoning about deep method differences inline.
  Relay its comparison to the user.
- **R5 — Critic advisory (optional, never a gate).** During design, if
  a paper's `critic_reviews.md` exists, the experimenter *may* consult
  it to surface claim/code uncertainties that bear on the experiment
  (e.g. a reproducibility caveat that affects a method's inclusion). Use
  it if present; degrade gracefully if not. **Never** force a critic run,
  and never block the design on it.
- **R6 — Stop at the implement boundary (current scope).** When the
  design is complete and written, tell the user the implement/run/
  evaluate phases await the `coder` and `evaluator` agents. Do not write
  code or run anything.
- **R7 — Inference discipline.** Carry the `[A]`/`[B]` prefixes
  (author-stated vs. reader-inferred) into hypotheses and rationale, as
  the critic and comparator do. No unsourced field-knowledge ranking of
  methods.

## Verification gate (inline, before writing `design.md`)

`design.md` can contain LaTeX (criterion definitions, hypotheses) and
citations. It lives under `experiments/<topic>/`, which the post-hoc
hook skips — so the experimenter gates inline, like the comparator.
Before declaring the design complete, run **LaTeX first, then
citations**, each with retry budget max 2, via the `latex-verifier` and
`citation-verifier` subagents (Mode A on the resolved `design.md` path;
pass the first paper slug as the citation cache key). Disclose remaining
findings if a budget is exhausted. Drafts with no math/citations skip
the relevant gate.

## Scope boundaries

- **Design only (current).** No code, no runs, no `findings.md` until
  the `coder` / `evaluator` ship.
- **Owns the data *design*, not the data *code*** (Seam A).
- **No conceptual deep-dive.** Method contrast is the `comparator`'s job
  (`comparison.md`); the experimenter cross-references it.
- **Vault writes limited to** `vault_experiments_dir(topic)/design.md`
  (and, later, `findings.md`). Code/data go to `repo_experiments_dir`
  via the `coder` — not the experimenter.

## Self-checks

Before reporting the design complete:

- All seven `design.md` sections present and in order.
- Criterion (§1) is falsifiable and every later section serves it.
- Data design (§4) commits to a pinned seed and names the stress lever.
- MVP (§5) names metrics, baselines, and seed count.
- Hypotheses and rationale carry `[A]`/`[B]` prefixes; no unsourced
  winner.
- Front-matter matches the multi-paper schema (`topic:` + `papers:`,
  `status: designed`).
- The inline LaTeX + citation gates ran (or were correctly skipped).
- The user was told the implement/evaluate phases are pending.
