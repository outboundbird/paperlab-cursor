---
name: ml-evaluation
description: Authoritative schema for `findings.md` — the empirical write-up the Evaluator produces from a Stage-2 experiment's run outputs. Defines the five fixed sections (header, hypothesis ledger, results, threats to validity, what the user can conclude), six variant runbooks for the Results section by `research_type` (methods comparison, ablation, reproduction, sensitivity, exploration, custom), the `[A]` / `[B]` / `[E]` inference tagging discipline (with structural-cell exception for ledger `Status` / `Notes`), the `[INSUFFICIENT-RUN]` flag for under-spec runs, the `[GATED-OFF]` flag for hypotheses gated on another's outcome, and the process the Evaluator follows. The Evaluator writes no PASS/FAIL — the user reads `findings.md` and judges. Use when an Evaluator subagent is invoked to write `findings.md`, or when reading / hand-editing one.
---

# ML Evaluation Schema

## Purpose

`findings.md` is the empirical counterpart of `comparison.md` (`ml-comparison`) and the empirical complement to `design.md` (`ml-experiment-design`). Where `design.md` declares what the experiment will test and how, `findings.md` reports what the run showed. The two files together let a reader reconstruct an experiment's full lifecycle without rerunning it.

`findings.md` is written by the **Evaluator** subagent, backend-only, invoked by the `experimenter` during the **Build-evaluate** sub-phase. Users read `findings.md` directly in Obsidian and judge the experiment's outcome themselves; the Evaluator does not return a PASS/FAIL.

## Where it lives

- Path: `vault_experiments_dir(topic)/findings.md`. Resolve via `tools/paths.py` — `python -m tools.paths exp-vault <topic>`.
- One per topic. Never per paper. The multi-paper convention applies (see "Front-matter").
- Regenerate-prompt rule (`.cursor/rules/paperlab-regenerate-prompt.mdc`) applies: on regenerate, ask **replace / append / abort**.

## Front-matter

Per `AGENTS.md` § "Multi-paper variant (experimenter suite)":

```yaml
---
topic: <topic>
papers:
- <slug-1>
- <slug-2>
category: experiment-findings
agent: evaluator
status: evaluated
sources:
- "[[experiments/<topic>/design.md]]"
concepts:
- "[[<concept-from-design>]]"
tags:
- AI-guided-paper-reading
- experiment-findings
---
```

Single-method experiments still use `papers:` as a list with one entry. Use the verbatim slug per `paperlab-config-bootstrap.mdc`.

## Schema — five fixed sections

The section names and order below are fixed across all `research_type` variants. Only the *body shape of section 3* adapts (see "Variant runbooks").

### 1. Header (after front-matter)

```markdown
# Findings — <topic>

**Question:** <one-line restatement from design.md §1>
**Methods:** <as in design.md>
**Run date:** <YYYY-MM-DD of the latest results JSON>
**Evaluation date:** <today>
**Sources audited:** <list of results JSON files, relative to repo_experiments_dir(topic)>
**Run completeness:** complete | partial | smoke (with [INSUFFICIENT-RUN] flag if applicable)
```

### 2. Hypothesis ledger

A markdown table with one row per hypothesis declared in `design.md` §3. No PASS/FAIL — status is one of:

- `supported` — the run produced the criterion specified in `design.md` §4.
- `not supported` — the run produced numbers that fall outside the criterion.
- `inconclusive` — flagged when the run cannot decide (always set when `[INSUFFICIENT-RUN]` is in notes).

Columns: **H#**, **Hypothesis (one line)**, **Criterion (from design.md §4)**, **Observed (this run)**, **Status**, **Notes**.

The Observed column carries the actual number(s) — mean ± std across seeds, the threshold, etc. Notes is where `[INSUFFICIENT-RUN]`, `[UNREADABLE]`, or scope qualifiers go. Tag each Observed cell with `[E]` (empirical) since it is by construction.

### 3. Results

Fixed name. The body follows the **variant runbook** for `design.md`'s `research_type` (see next section). Within Results, every numerical claim carries `[E]`; framing claims carry `[B]` or `[A]` as appropriate.

The Results section is the report. It is the longest section and may have sub-headings.

### 4. Threats to validity

A bullet list of factors that limit what the user can conclude from the numbers. Mostly `[B]`-tagged. Cover:

- Run completeness (`[INSUFFICIENT-RUN]` reasons).
- Seed budget vs. variance reported.
- Metric–hypothesis alignment (does the metric the design specified actually answer the hypothesis it's tied to?).
- Confounds present in the data-synthesis design (referencing `design.md` §6 if relevant).
- External validity (the design's scope, transferred to "outside this scope, this run says nothing").

If you find none, write *None observed.* — do not pad.

### 5. What the user can conclude

The strict intersection of (a) what `design.md` actually tested and (b) what the numbers show. Three short paragraphs at most. Each sentence carries `[E]`, `[B]`, or `[A]`. This section is **not** a verdict; it is a careful re-statement of what the experiment lets the user say truthfully.

## Variant runbooks (the Results section's body)

One short checklist per `research_type`. The runbook tells you what tables / sub-sections to produce. Within each, every numerical cell is `[E]`.

### methods comparison

- **Head-to-head per metric.** Table: rows = methods, columns = metrics; mean ± std across seeds.
- **Where each method wins.** Per-metric: which method is best, by how much, on which slice.
- **Statistical-significance note.** State whether the seed budget supports significance claims; if it does not, say so explicitly. (Common case: insufficient.)
- **Per-paper extension fidelity.** If the run is via `coder` Stage-2 component surgery, repeat the per-paper extraction-fidelity verdict from the critic gate (it ran pre-run; restate so the user has the full chain).
- **Failure modes.** Conditions under which one or more methods broke down or returned NaN.

### ablation

- **Component drops table.** Rows = component-removed configurations; columns = the design's metric(s). Include the full-model row as the reference.
- **Ranked drops.** Sort components by largest-to-smallest effect. State which components carry the weight.
- **Interaction effects.** If multiple components were ablated jointly, report the combined drop and compare to the sum of singles. Flag super-additive or sub-additive interactions.
- **Failure boundary.** The smallest configuration that still meets the design's criterion (if any).

### reproduction

- **Paper-claim vs. our-run side by side.** Table: rows = the paper's reported numbers (with citation §); columns = paper-claim, our-run, delta.
- **Where ours diverges.** Per row that diverges by more than the design's tolerance, write a short prose paragraph naming the most likely cause (data preprocessing, hyperparameter, seed, framework version) — clearly tagged `[B]` since it is inference, not measurement.
- **Reproducibility verdict.** *Not* a PASS/FAIL — a per-claim verdict: reproduced / partially reproduced / not reproduced / inconclusive. The user reads and judges the design as a whole.

### sensitivity

- **Trend across the swept axis.** Table or compact figure description: metric values across the swept parameter values, mean ± std across seeds at each point.
- **Phase boundary.** Identify the value(s) of the swept axis at which the metric crosses the design's criterion.
- **Robustness verdict.** *Per swept axis*, plain-prose description: stable across the swept range / smooth degradation / sharp phase transition / unstable. With `[E]` tags.
- **Out-of-scope note.** State explicitly that the run says nothing about values outside the swept range.

### exploration

- **Is the phenomenon present?** One sentence per hypothesis: yes / no / inconclusive, with the observed number.
- **Per-H# walkthrough.** A short paragraph per hypothesis, working through the evidence and what it shows.
- **Surprises.** Anything the run produced that the design did not predict. Tag `[E]` for the observation, `[B]` for any speculative interpretation.
- **Phenomenon strength vs. design's threshold.** How close are the numbers to the design's criterion? Knife-edge or comfortable?

### custom

The Evaluator picks two or three of the runbook patterns above that fit the experiment, and writes a one-line note in Results explaining the choice. If nothing above fits, write Results as free-form prose with a short "Why custom" note up front. Maintain the `[A]` / `[B]` / `[E]` tagging regardless.

## Inference discipline — `[A]` / `[B]` / `[E]`

Mandatory in every section past the front-matter. A bare claim is a defect.

- `[A]` — anchored in a paper (cite `spec.md §` or the references in `design.md`).
- `[B]` — reader-inferred from the design's framing or general field background. Theoretical, not measured.
- `[E]` — empirically grounded **by this run**: read off the JSON or computed from it without further argument.

Mixing types in one sentence is forbidden. Split it.

The Results section is mostly `[E]`. Threats to validity is mostly `[B]`. The "What the user can conclude" section is `[E]`-claims filtered by `[A]` / `[B]` scope.

**Structural cells.** The Hypothesis ledger's `Status` and `Notes` cells are structural, not claim-bearing — `Status` is a controlled vocabulary (`supported` / `not supported` / `inconclusive`) and `Notes` carries flags (`[INSUFFICIENT-RUN]`, `[GATED-OFF]`, `[UNREADABLE]`, scope qualifiers). Do **not** tag these cells with `[A]` / `[B]` / `[E]`. The "every claim past the header" rule applies to *claim-bearing* prose and numerical cells (e.g. the `Observed` cell, which is by construction `[E]`).

## `[INSUFFICIENT-RUN]` flag rule

A hypothesis is `[INSUFFICIENT-RUN]` when the executed run does not let you decide it. Triggers:

- **Smoke run.** The JSON's `config` block shows materially smaller epochs / dataset size / fewer seeds than the design specifies. The threshold is judgment — a `--smoke` flag set to `true`, or fewer than half of the design's seeds, is enough.
- **Missing metric.** The hypothesis names a metric the JSON does not contain.
- **Errored run.** The JSON reflects an incomplete trajectory (NaN losses, early termination, no test-set numbers).
- **Off-spec config.** The JSON config differs from `design.md`'s spec in ways material to the hypothesis (different `mu`, different `N`, different optimizer, etc.) — but the design did not mark this as a swept axis.

When triggered:

- The ledger row's status is `inconclusive`.
- The Notes cell carries `[INSUFFICIENT-RUN]: <reason>`.
- The Threats-to-validity section repeats the flag with the affected hypothesis number.
- The Results section still reports the numbers that exist, prefixed with the flag.

You do **not** refuse to write `findings.md`. Refusal is the experimenter's job, pre-invocation.

### Gating hypotheses ([GATED-OFF])

A hypothesis is **gated** when its interpretability is conditional on another hypothesis being supported first. Concrete example: H3 "recovery quality indicates IB compression" gated by H1 "test accuracy ≥ 0.75" — without H1, H3's recovery numbers exist but cannot be interpreted as compression evidence. Gating is declared in `design.md` §3 as part of the hypothesis statement (e.g. "Conditional on H1 being supported, ...").

Gating is **distinct from `[INSUFFICIENT-RUN]`**: the run can be fully spec-compliant (correct seeds, correct config, full epochs) while the chain of inference is broken because an upstream hypothesis failed. A separate flag `[GATED-OFF]` keeps the threats-to-validity narrative honest.

When the gating hypothesis (the upstream one) ends with status:

- `not supported` → the gated hypothesis's status becomes `inconclusive`; Notes cell carries `[GATED-OFF]: depends on H<n>, which is not supported`.
- `inconclusive` (e.g. `[INSUFFICIENT-RUN]` or another `[GATED-OFF]`) → the gated hypothesis inherits `inconclusive`; Notes cell carries `[GATED-OFF]: depends on H<n>, which is inconclusive`. (Chains transitively.)
- `supported` → the gated hypothesis is evaluated normally; no `[GATED-OFF]` flag.

In all `[GATED-OFF]` cases:

- The ledger row's `Observed` cell still reports the numerical value the run produced (`[E]`-tagged) — for transparency, not as evidence.
- The Threats-to-validity section repeats the flag with the affected hypothesis number and the upstream hypothesis it depended on.
- The Results section reports the gated numbers but prefixes them with the flag and explicitly says they cannot be read as evidence for the gated hypothesis.
- The "What the user can conclude" section does not draw conclusions from a gated-off hypothesis.

## Process

1. **Resolve paths.**
   - `design_path = vault_experiments_dir(topic) / "design.md"` if not provided.
   - `results_dir = repo_experiments_dir(topic) / "run" / "results"` if not provided. (Some experiments may use a different path; honor what the experimenter passed.)
   - `findings_path = vault_experiments_dir(topic) / "findings.md"`.
2. **Read `design.md`.** Extract:
   - `topic`, `papers`, `research_type` from front-matter.
   - §1 question.
   - §3 hypotheses (H1, H2, ...) with their criterion-relevant phrasing.
   - §4 criterion (the metric and threshold).
   - §5.1 method spec (for context only; the Evaluator does not re-derive method math).
   - §6 data-synthesis design (epoch / N / seeds / mu / data_seed) — for the completeness check.
3. **Read every results JSON** under `results_dir`. Common shape: `config`, `per_seed`, `aggregate`, `hypothesis_thresholds`. If the JSON is malformed, log `[UNREADABLE]` and skip.
4. **Completeness check.** For each hypothesis:
   - Compare the JSON `config` block to `design.md` §6 / §5.1 spec. If smaller (smoke / fewer seeds / different mu) → flag `[INSUFFICIENT-RUN]`.
   - Confirm the metric the hypothesis depends on is present in `aggregate` or computable from `per_seed`. If not → flag.
5. **Fill the schema.** Five fixed sections (header, ledger, results, threats, conclusions). The Results section follows the variant runbook for `design.md`'s `research_type`.
6. **Tag every claim.** `[A]` / `[B]` / `[E]`. Mandatory. Run a self-check pass before returning.
7. **Regenerate prompt.** If `findings.md` already exists, stop and surface the replace / append / abort prompt to the experimenter (which surfaces it to the user). First-time writes proceed.
8. **Inline LaTeX verification gate.** `findings.md` lives under `experiments/<topic>/`, which the post-hoc verifier hook skips, so the Evaluator gates LaTeX inline before returning. Run `latex-verifier` Mode A on the resolved `findings.md` path. PASS (no error-severity findings) → continue; warnings do not block. FAIL → fix each named error, rewrite, re-verify. Max 2 retries; if still failing, **disclose** the remaining errors in the return summary rather than emitting silently. Drafts with no math skip the gate. **No citation gate** — `findings.md` introduces no novel external citations: `[A]` paper-anchored claims resolve to references already verified upstream (`spec.md` LaTeX-gated by the dissector; `comparison.md` inline-gated by the comparator). Revisit if a hallucinated citation lands in `findings.md` in practice (`AGENTS.md` § Verifier system records the trigger).
9. **Return.** Path of the written `findings.md` plus a one-paragraph summary (≤ 6 sentences). No PASS/FAIL. Include the LaTeX gate outcome ("LaTeX gate: clean" / disclosed errors).

## Scope boundaries

- One file out: `findings.md`.
- No code execution, no metric recomputation from checkpoints, no model retraining.
- No edits to `design.md`, `spec.md`, `code_map.md`, `comparison.md`, or any per-paper file.
- No `/evaluator` user command. Backend-only.
- No PASS/FAIL on the design as a whole. The hypothesis ledger reports `supported` / `not supported` / `inconclusive` per H#; the user judges the design from there.
- No follow-up-experiment proposals. The user reads `findings.md` and decides; the experimenter facilitates.

## Self-check before returning

Before returning to the experimenter, verify:

- Front-matter has all required keys with the multi-paper convention (`topic:` + `papers:` list).
- Five sections exist in order: Header, Hypothesis ledger, Results, Threats to validity, What the user can conclude.
- The Results section follows the runbook matching `design.md`'s `research_type`.
- Every hypothesis declared in `design.md` §3 has a row in the ledger.
- Every claim outside the front-matter and Header carries `[A]`, `[B]`, or `[E]`.
- Every `[INSUFFICIENT-RUN]` flag in the ledger is repeated in Threats to validity.
- Every `[GATED-OFF]` flag in the ledger names the upstream hypothesis it depends on; the upstream hypothesis's status is consistent with the gated row's status (gating chain checks out).
- The "What the user can conclude" section does not announce a verdict on the design as a whole.
- No PASS/FAIL anywhere. No "the experiment shows that ..." absolutism — keep claims tagged.
- The inline LaTeX gate ran (or was correctly skipped — no math) and its outcome is in the return summary.
