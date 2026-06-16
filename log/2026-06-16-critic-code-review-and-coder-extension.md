# 2026-06-16 — Critic `code_review.md` split + Coder Stage-2 extension regime

Two carry-over fixes from the GIBGAT smoke run (see
[`2026-06-15-experimenter-skill-conversion.md`](./2026-06-15-experimenter-skill-conversion.md)
and the GIBGAT experiment under `sandbox/experiments/gib-importance/`).
Batched together because they touch overlapping files and represent the
same shape of fix: the Stage-2 fork was implicit; we made it explicit.

## What broke

1. **Critic appended to `critic_reviews.md` without prompting.** During
   the GIBGAT run the critic re-audited under the `reconstructed`
   source and silently appended a fidelity audit to the existing
   `critic_reviews.md` (which had been written under the `official`
   source). That violates `.cursor/rules/paperlab-regenerate-prompt.mdc`,
   and even with the prompt it would have been the wrong fix — the two
   audits are different artifacts and shouldn't have been hosted in the
   same file in the first place.

2. **Single-method experiments don't fit Stage-2 component surgery.**
   The GIBGAT experiment is one paper studied via planted-signal
   recovery — a single-method sensitivity / ablation hybrid. Stage-2 was
   designed exclusively for component surgery (≥ 2 papers, scaffold +
   extracted components, extraction-fidelity gate). The agent improvised
   into `sandbox/experiments/gib-importance/` with a layout that does
   not match either the documented Stage 2 or any other documented
   regime, and the critic's extraction-fidelity gate has nothing to
   compare across.

Both bugs come from the same place: the design assumed Stage 2 = the
multi-method case, and there was no documented branch for the
single-method case. The tooling silently degraded into improvisation.

## Fix #1 — `code_review.md` as a sibling of `critic_reviews.md`

The audit's *target file* now depends on the `code_map.md` §1 **Source**
field:

- `official` → `vault_path(slug, "critic_reviews.md")` (existing
  convention, unchanged).
- `reconstructed` → `vault_path(slug, "code_review.md")` (new sibling
  file, same schema).

Same schema, different file. A paper audited under both sources keeps
both audits. The regenerate-prompt rule applies to whichever target the
current source maps to — first-time writes don't trigger the prompt.

The H1 / `category:` differ so each file is self-identifying:

- `critic_reviews.md`: `# Critic Reviews — <slug>`, `category: model`.
- `code_review.md`: `# Code Review — <slug>`, `category: model-review`.

### Files edited (#1)

- `.cursor/agents/critic.md` — front-matter description, role, process,
  audit-source modes, self-check, reporting-back.
- `.cursor/skills/ml-critique/SKILL.md` — front-matter description,
  Purpose, §1 header (split into per-source variants).

### Migration of the existing GIBGAT file

The user owns the call; both options are reasonable:

- **Migrate.** Split the GIBGAT `critic_reviews.md` into the official
  audit (kept) + a new `code_review.md` (the appended reconstructed
  audit, moved out). One-time manual edit.
- **Leave as a one-off.** Mark it in the file's preamble as
  pre-2026-06-16 layout. New audits start from this date follow the
  split.

This log doesn't pick — flagged here so it's not lost.

## Fix #2 — Stage-2 extension regime (single-method)

Stage 2 now has two regimes, picked by `design.md` member count:

| Regime | Members | Coder writes | Critic gate |
|---|---|---|---|
| Component surgery | ≥ 2 | `scaffold.py` + `methods/<slug>/extracted.py` + `run.py` | extraction-fidelity (Check A per paper, Check A1 wiring, Check B scaffold) |
| Extension | exactly 1 | `methods/<slug>/extended.py` + `synth/generate.py` + `run.py` | extension-fidelity (Check A extension, Check A1 wiring; no Check B — no scaffold) |

The extension regime's defining constraint: `extended.py` must
**inherit from or compose** the audited Stage-1 `method.py` (or the
upstream code referenced through `code_map.md`). It must not copy or
hand-reimplement the base method. Anything the experiment varies must
be expressible as an override or a wrapper, otherwise it's surfaced to
the experimenter rather than rewritten in place.

The §5.2 seam contract (multi-method only) is replaced for single-method
experiments by a **research-type variant** in `design.md` — ablation
table, sensitivity sweep, reproduction criteria, planted-signal probe,
or custom — which doubles as the **extension scope** the experimenter
passes to the coder. The research-type table now records which regime
each row maps to.

If a single-method experiment grows a second member later, the
experimenter promotes it to component surgery — a deliberate
`design.md` edit, not a silent regime change.

### Files edited (#2)

- `.cursor/skills/ml-experiment-code/SKILL.md` — added `STAGE 2 —
  Extension regime` section (file layout, what `extended.py` may /
  may not do, provenance header, fidelity gate pointer, process,
  self-checks, scope boundaries); updated front-matter description.
- `.cursor/agents/coder.md` — front-matter description, two-stages
  preamble, route detection, Stage-2 process split into "component
  surgery" + "extension regime" sub-processes, reporting-back
  variants, scope boundaries.
- `.cursor/skills/ml-critique/SKILL.md` — added `Extension-fidelity
  mode` section (Check A, Check A1, no Check B, verdict rules,
  reporting back); updated front-matter description.
- `.cursor/agents/critic.md` — added "extension-fidelity mode" to the
  description, role, invocation pointer.
- `.cursor/skills/experimenter/SKILL.md` — Implement hand-off split
  by member count; "Invoking the coder" split by regime; both routes
  named with their gates.
- `.cursor/skills/ml-experiment-design/SKILL.md` — research-type
  variants section reframed as "extension scope"; research-type
  table gains a coder-regime column.

## Files edited (#3 — cross-cutting docs)

- `AGENTS.md` — `status` vocabulary entry mentions both audit files;
  vault file list adds `code_review.md`; critic entry rewritten to
  describe the two-file split + new extension-fidelity gate; coder
  entry rewritten to describe the two Stage-2 regimes; experimenter
  entry's Build-phase line names both regimes.
- `log/2026-06-16-critic-code-review-and-coder-extension.md` (this
  file).

## Why batch them

The two fixes touch the same files (`ml-critique/SKILL.md`,
`critic.md`, `experimenter/SKILL.md`, `AGENTS.md`) and the same mental
model — "Stage 2 has more than one shape, name them." Doing them in
one pass keeps the cross-references consistent and avoids a mid-batch
state where the critic gate names a regime the coder doesn't
implement, or vice versa.

## Open follow-ups

- Migration call on the existing GIBGAT `critic_reviews.md` (see
  above).
- The `evaluator` is still not built, so extension-regime experiments
  run to **results emitted** only — same stop boundary as
  component-surgery experiments.
- Behavioral-equivalence in extension regime is "the neutral setting
  reproduces the base method." For ablations / sensitivity sweeps with
  a clean neutral point this is a free check; document examples once
  we've run a few.
- The GIBGAT improvised layout (`sandbox/experiments/gib-importance/`
  with `methods/extended_gibgat.py` rather than
  `methods/<slug>/extended.py`) doesn't match the new spec. If we keep
  the run, leave it as a pre-2026-06-16 artifact and don't backport.
