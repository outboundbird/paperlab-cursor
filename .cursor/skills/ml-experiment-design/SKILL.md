---
name: ml-experiment-design
description: Schema for `design.md` — the recorded plan of an empirical experiment built around one or more papers. Defines the section kit and common research types (methods comparison, ablation, reproduction, sensitivity, exploration, custom). Read by the experimenter only after the user has confirmed they want a design written up. Files live at `vault_experiments_dir(topic)/`.
---

# ml-experiment-design

`design.md` is the **plan document** for an empirical experiment. It
records the design the user and experimenter built together in
conversation — what the experiment is for, what it measures, and how
it will be carried out — so the `coder` (Stage 2) and `evaluator`
agents can realize it.

This skill defines:

- The `design.md` schema as a **kit of parts**: mandatory sections
  every experiment needs, plus a conditional section (§5.2) that
  depends on the experiment's research type.
- A short **research type table** (methods comparison, ablation,
  reproduction, sensitivity, exploration, custom) — what each type
  typically uses from the kit.
- The verification gate the experimenter runs before declaring the
  design complete.
- The `findings.md` schema (write-path pending the `evaluator`).

It does **not** define the experimenter's interaction protocol —
that lives in `.cursor/agents/experimenter.md`. The conversation is
the agent's job; this skill is the schema the agent serializes once
the user has confirmed the plan.

## When this skill applies

The experimenter reads this skill **only after** the user has
explicitly signaled they want the discussion written up as a design,
and the experimenter has summarized the plan (and the section sketch)
in chat for the user to confirm. If you are reading this skill before
that point, stop and return to discussion.

The agent picks which schema sections apply to a given experiment from
the kit below, sketches the section list to the user, and writes
`design.md` only after the user confirms both the content and the
structure.

## Where files live

Resolve via `tools/paths.py` — never hard-code:

- `vault_experiments_dir(topic)/design.md` — the experiment plan.
  Written by the experimenter at the end of the Plan phase.
- `vault_experiments_dir(topic)/findings.md` — results write-up.
  Schema documented below; written from the `evaluator`'s output
  **once the evaluator exists**.
- `vault_experiments_dir(topic)/comparison.md` — conceptual comparison
  written by the `comparator` (its own skill, `ml-comparison`).
- `repo_experiments_dir(topic)/` — code and data (the `coder`'s
  territory: `synth/`, `methods/`, `run/`, `results/`, git-ignored
  `data/`).

`<topic>` is **user-chosen** (a problem class, not a paper slug).
Use it verbatim; if it is not a valid path segment, the agent asks
for an alternative.

## `design.md` — kit of parts

Eight top-level sections, with §5 (Methods) holding sub-sections.
Sections 1, 2, 3, 4, 5.1, 5.3, 6, 7, 8 are **mandatory** for every
experiment. §5.2 is **conditional** on the research type.

| § | Section | Status |
|---|---|---|
| 1 | Header / front-matter | mandatory |
| 2 | Problem setup | mandatory |
| 3 | Hypotheses | mandatory |
| 4 | Question and criterion | mandatory |
| 5 | Methods | mandatory (parent) |
| 5.1 | Methods used | mandatory |
| 5.2 | Comparison seam (or research-type variant) | conditional |
| 5.3 | Minimum viable comparison | mandatory |
| 6 | Data-synthesis design | mandatory |
| 7 | Decision rationale | mandatory |
| 8 | Uncertainty flags | mandatory |

The agent **sketches the section list explicitly to the user during
Plan phase** (see `experimenter.md`) and confirms it before writing.

### §1. Header / front-matter

```markdown
---
topic: <topic>
papers:
- <slug_a>
- <slug_b>
category: experiment
agent: experimenter
status: designed
research_type: <methods-comparison | ablation | reproduction | sensitivity | exploration | custom>
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

**Question:** one-sentence statement of what the experiment answers
**Methods:** <slug_a>, <slug_b>
**Date:** YYYY-MM-DD

---
```

`status: designed` is the experiment-suite lifecycle value for a
completed design. `research_type:` records the experiment's shape so
the graph index and downstream agents can branch on it. Quote any
YAML-special slug.

### §2. Problem setup

A record of what the user said about what the experiment is for.
Authored from the Plan-phase conversation, not from a spec scan.
Capture:

- **Problem class / task.** What is the prediction problem? Be
  concrete about granularity and target (node-level vs. graph-level
  vs. edge-level; classification vs. regression vs. structure
  recovery; transductive vs. inductive). For non-graph experiments,
  state the analogous task structure.
- **Motivating question.** Why is the user running this experiment?
  What do they want to learn or decide? One paragraph in the user's
  framing.
- **Why these papers.** For each candidate paper, what it is *for*
  (its native task) and why it is a candidate here. Sourced from
  each `spec.md` §3 only after the user has named the candidates in
  conversation.
- **Shared-task check** (when comparing methods across papers).
  Confirm that the candidate methods address the same problem class.
  If they do not, the mismatch was surfaced to the user in
  conversation; record the resolution here (reframe, swap, or
  bridge with confounds noted in §8).

Every later section serves the problem framed here. If the framing
changes, revisit them.

### §3. Hypotheses

Falsifiable predictions about each method's behavior on the problem
setup. **Hypotheses are not rankings.** They predict measurable
behavior — e.g. "Method M identifies contributing neighbor nodes with
≥ 80% accuracy on the §6 synthetic data" — and the experiment
confirms or refutes them.

Each hypothesis names which method(s) it concerns and what result
would confirm or refute it. Mark predictions the papers themselves
make as `[A]` (author-stated) vs. inferred predictions as `[B]`
(reader-inferred). Do not crown a winner here — these are
predictions, not conclusions.

Hypotheses come **before** the formal criterion (§4) because they are
the user's predictions in their own framing; the criterion (§4)
operationalizes the property the hypotheses imply.

### §4. Question and criterion

State the empirical question precisely: *what property* of the
methods is being tested (e.g. expressivity, sample efficiency,
robustness to distribution shift, fidelity of attribution), and *why
it matters* for the problem class. One paragraph.

The criterion operationalizes the hypotheses (§3): it names the
property that, when measured, confirms or refutes them. Every later
section serves this criterion.

### §5. Methods

#### §5.1 Methods used

One short subsection per method (or per variant for an ablation; per
candidate for a reproduction). For each:

- **Name** and the **paper** it comes from.
- **Approach** — one to two sentences on how the method addresses
  the problem class. Sourced from each paper's `spec.md`; deep
  conceptual contrast belongs in `comparison.md`, not here.
- **How performance is measured for this experiment.** What metrics
  (accuracy, precision, recall, loss, attribution fidelity, ...) will
  prove §3's hypotheses right or wrong for this method. State the
  link between the chosen measurement and the §3 prediction —
  measurement is whatever decides the hypothesis, not necessarily the
  method's native loss.

If a `comparison.md` already exists for this topic, cross-reference
it with a `[[wiki-link]]` rather than restating its content.

#### §5.2 Comparison seam (conditional — applies to methods comparison)

The **seam** is *where* the comparison cuts: the shared principle +
task the experiment holds **fixed**, and the **divergent component**
each method swaps in. It is the scientific claim of the experiment
— fix too little and incidental differences contaminate the result;
fix too much and you erase the difference you meant to measure.

This section is read directly by the `coder` in Stage 2 (component
surgery) to synthesize the shared scaffold and extract each method's
component, so it must be concrete. Record:

- **Held fixed (the principle + task).** The shared mechanism every
  method assumes (e.g. the information-bottleneck objective $I(X;Z)
  - \beta I(Z;Y)$) and the common task (e.g. node classification on
  the synthetic graphs of §6). This becomes the scaffold's fixed
  pipeline.
- **The pluggable slot (what varies).** The one component being
  compared (e.g. the bottleneck sampling/selection step), named
  precisely, with its inputs and output — the **union** across
  methods (if one method's component needs an input another ignores,
  list it; the slot carries both).
- **Per method, the divergent component + its source.** For each
  slug, name the component and where it lives in that paper
  (`code_map.md §`/function), so the coder can locate and extract
  it.
- **⚠️ UNCERTAIN** if a method's component cannot be cleanly
  separated, or two methods cannot share one faithful seam.
  Recorded here at design time; if it surfaces during coding, also
  recorded in `findings.md`.

Keep to one slot per experiment by default (clean attribution of the
measured difference to the divergence point); only add a second with
explicit rationale.

**Research-type variants** (replace §5.2 when the experiment is not a
methods comparison):

- **Ablation table.** Name each component being ablated and what
  removing it tests.
- **Reproduction success criteria.** Specify the reported numbers
  being matched and the tolerance for "matches" (e.g. accuracy
  within 1%, rank order preserved).
- **Sensitivity sweep table.** Name the parameter swept and its
  range.
- **Custom research type.** If the experiment doesn't fit the types
  above, the agent proposes a new section structure during Plan
  phase, captures the user-confirmed structure here, and flags the
  schema as novel in §8.

#### §5.3 Minimum viable comparison

The smallest experiment that answers §4 honestly:

- **Metrics** — what is measured across methods, and how each maps
  to the criterion (§4).
- **Baselines** — what the methods are compared against (including
  any trivial baseline).
- **Seeds / repetitions** — how many runs, to gauge variance.
- **Out of scope** — what is deliberately excluded to keep the
  experiment small.

### §6. Data-synthesis design (Seam A — owned by the experimenter)

The data plan, recorded for the `coder` to implement:

- **Generative process** — what distribution / structure the
  synthetic data has, and how it is parameterized.
- **Stress lever** — the knob that stresses the criterion (size,
  density, noise level, distribution-shift magnitude, ...). What is
  varied and over what range.
- **Synthetic vs. small real** — which, and why.
- **Pinned seed** — the design commits to a seed so data is
  regenerable (data itself is git-ignored).

### §7. Decision rationale

Why these choices over alternatives. Capture the trade-offs
discussed with the user so the design is self-explaining on re-read.
The analogue of a design log's decision record, scoped to one
experiment.

### §8. Uncertainty flags

Anything ambiguous or unresolved, each prefixed `⚠️ UNCERTAIN:` (per
`AGENTS.md`). Examples: a criterion that is hard to operationalize,
a method whose `spec.md` is too thin to implement faithfully, a data
design that may not isolate the property cleanly, a novel section
structure introduced for a custom research type.

## Research type table

The agent uses this during Plan phase to sketch the section list.
**Not a template the agent fills** — a guide for which sections the
kit needs assembled for each research type.

| Research type | §5.1 framing | §5.2 (conditional) | Notes |
|---|---|---|---|
| Methods comparison | Per-paper method | Comparison seam | Multi-paper. |
| Ablation | Variants of one method | Ablation table | One paper. §3 hypotheses predict per-component contribution. |
| Reproduction | The model under reproduction | Reproduction success criteria | One paper. §3 hypotheses are "matches reported numbers within tolerance". |
| Sensitivity sweep | Method(s) under sweep | Sensitivity sweep table | One or more methods. §3 hypotheses predict the response curve. |
| Exploratory probe | Method whose behavior is probed | (often none) | One method. §3 hypotheses are looser — predict a phenomenon, not a number. |
| Custom | User-defined | User-defined | Agent proposes structure mid-conversation; flag novel schema in §8. |

If the user proposes a research type not on this list, the agent
sketches a section structure with the user during Plan phase, gets
confirmation, and writes `design.md` accordingly with a §8 note.

## `findings.md` — schema (write-path pending `evaluator`)

Documented now so the schema is stable; the experimenter writes this
from the `evaluator`'s output **once the evaluator ships**. Until
then, do not create this file.

### §1. Header

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

1. **Result summary** — what happened, against each hypothesis (§3
   of `design.md`): confirmed / refuted / inconclusive, with the
   numbers.
2. **Per-metric results** — tables/figures the `evaluator` produced.
3. **Interpretation** — what the results mean for the criterion.
   Empirical superiority can be named here on measured grounds
   (unlike `comparison.md` and unlike `design.md` §3).
4. **Threats to validity** — seeds, variance, design limitations
   from `design.md` §5.3 and §8 that bear on the conclusion.
5. **Uncertainty flags** — `⚠️ UNCERTAIN:` as needed.

## Verification gate (inline, before writing `design.md`)

`design.md` lives under `experiments/<topic>/`, which the post-hoc
verifier hook skips. The experimenter runs the gate inline before
declaring the design complete.

Run **LaTeX first, then citations**, each with retry budget max 2:

1. **LaTeX gate.** `latex-verifier` Mode A on the resolved
   `design.md` path. PASS → continue. FAIL → fix each named error,
   rewrite, re-verify. Max 2 cycles; if still failing, disclose
   remaining errors in the report.
2. **Citation gate.** `citation-verifier` Mode A on the same file,
   passing `--slug <first paper slug>` (cache key). PASS (no
   `mismatched`) → done; surface any `unresolved` warnings without
   blocking. FAIL → fix, rewrite, re-verify. Max 2 cycles; disclose
   remaining mismatches if exhausted.

Drafts with no math/citations skip the relevant gate.

## Self-checks

Before reporting the design complete:

- The user explicitly switched the session from Plan to Build before
  any file write.
- The agent summarized the plan + section sketch in chat and the
  user confirmed before the file was written.
- All mandatory sections (1, 2, 3, 4, 5.1, 5.3, 6, 7, 8) present and
  in order.
- §5.2 (or its research-type variant) present if the research type
  requires it; absent if it does not.
- Front-matter records `research_type:` and matches the multi-paper
  schema (`topic:` + `papers:`, `status: designed`).
- §3 hypotheses are predictions of method behavior on the setup,
  not rankings. `[A]`/`[B]` prefixes carried.
- §4 criterion is falsifiable and operationalizes §3.
- §5.1 records, per method, how performance is measured for this
  experiment and how that measurement decides §3.
- §5.2 (when present) names the held-fixed principle + task, the
  pluggable slot with union I/O, and per-method the divergent
  component + `code_map.md` source — concrete enough for the coder.
- §6 commits to a pinned seed and names the stress lever.
- §5.3 names metrics, baselines, and seed count.
- The inline LaTeX + citation gates ran (or were correctly skipped).
- The user was told the implement / evaluate hand-off status.
