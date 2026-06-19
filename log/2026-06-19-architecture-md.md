# 2026-06-19 — `ARCHITECTURE.md` and documentation split

## Summary

Introduced [`ARCHITECTURE.md`](../ARCHITECTURE.md) as the **design / orchestration** home: goals and non-goals, design principles, two-suite flow (with the same Mermaid diagrams as before), file layout contract, memory sharing (single-writer table + small cross-suite bridge diagram), verifier system **conceptual** narrative, YAML/graph-index summary, decision framework (moved from `ROADMAP.md`), and pointers.

Slimmed [`README.md`](../README.md) to **quick start** + **documentation map** (links to `ARCHITECTURE.md`, `AGENTS.md`, `ROADMAP.md`, `log/`).

[`ROADMAP.md`](../ROADMAP.md): replaced the long **File layout contract** and **Decision framework** bodies with stubs pointing at `ARCHITECTURE.md`; kept machine-specific `vault_paperlab_path` line and the Agents table. Added **Reference: documentation** subsection before **Reference: what's currently working**. Corrected the `experimenter` row (removed stale “findings awaits evaluator”). Updated **No citation gate** “See” line to cite `ARCHITECTURE.md` / `AGENTS.md` instead of a removed `AGENTS.md` asymmetry subsection title.

[`AGENTS.md`](../AGENTS.md): **Verifier system** is now **operational-only** (inline gate, post-hoc hook, cache, tool names) with a pointer to `ARCHITECTURE.md` for the full conceptual picture. YAML / multi-paper / graph-index paragraphs link to `ARCHITECTURE.md` where layout or verifier context moved.

## Skills touched (link hygiene only)

Cross-references inside verifier- and graph-related skills were updated so they do not point at removed `AGENTS.md` subsection titles or at a non-existent `ROADMAP.md` “Verifier system” anchor:

- `.cursor/skills/ml-latex-verify/SKILL.md`
- `.cursor/skills/ml-citation-verify/SKILL.md` (per-paper cache note + “Where this fits”)
- `.cursor/skills/ml-evaluation/SKILL.md` (citation revisit trigger)
- `.cursor/skills/ml-experiment-design/SKILL.md` (same, for `design.md`)
- `.cursor/skills/concept-vocabulary.md` (`reindex` / graph index pointers)

No skill **protocol** or gate logic was changed—only documentation links and wording around where to read the architecture vs operational split.

## Revision (same day) — `AGENTS.md` canonical for agents

User direction: **`AGENTS.md` stays the single normative reference for subagents and skills**; [`ARCHITECTURE.md`](../ARCHITECTURE.md) is **human-facing only** (orchestration narrative, diagrams). Changes:

- Restored the **full Verifier system** section in [`AGENTS.md`](../AGENTS.md) (conceptual + operational + tool layer, as before the split).
- Added **Decision framework** to [`AGENTS.md`](../AGENTS.md) (same bullets as in `ARCHITECTURE.md`); [`ROADMAP.md`](../ROADMAP.md) stub now points at `AGENTS.md` first, `ARCHITECTURE.md` second for humans.
- [`ARCHITECTURE.md`](../ARCHITECTURE.md): explicit **Audience** banner; verifier and decision-framework sections labeled as reader digests with normative copy in `AGENTS.md`.
- [`README.md`](../README.md) documentation map: `AGENTS.md` listed first as authoritative; `ARCHITECTURE.md` labeled human-oriented / non-normative for agents.
- [`ROADMAP.md`](../ROADMAP.md) file-layout stub: **subagents** → `AGENTS.md` § Where things live; **human trees** → `ARCHITECTURE.md` § File layout contract.
- Reverted skill cross-references (`ml-latex-verify`, `ml-citation-verify`, `ml-evaluation`, `ml-experiment-design`, `concept-vocabulary`) to **`AGENTS.md` / `ROADMAP.md` only** — no skill points at `ARCHITECTURE.md` for verifier triggers.

## Follow-ups

- Optional: add `ARCHITECTURE.md` to `paperlab.config.example.yaml` comment block if we want config readers to see the doc map (not done).
- Historical logs under `log/` that still say “architecture in `AGENTS.md`” are left as-is (dated record).
