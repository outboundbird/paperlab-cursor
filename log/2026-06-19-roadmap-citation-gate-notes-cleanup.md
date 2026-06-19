# 2026-06-19 — ROADMAP cleanup: citation-gate reframe + drop notes.md sync

Small documentation-only pass on [`ROADMAP.md`](../ROADMAP.md). No code or skill behavior changed.

## Changes

1. **Citation gate on `design.md` / `findings.md` reframed as a deliberate decision.**
   Moved the entry out of **Known limitations** (which reads as an unmet gap) into **Deferred features**, retitled *"Citation gate on `design.md` / `findings.md` — intentionally omitted"* and rewritten to lead with "deliberate design choice (settled 2026-06-18)". The revisit trigger is preserved verbatim (add a citation gate only if a hallucinated arXiv ID / DOI / URL / mismatch is observed in practice). The underlying decision is unchanged — see [`log/2026-06-18-experimenter-evaluator-latex-gate.md`](./2026-06-18-experimenter-evaluator-latex-gate.md).

2. **Dropped the deferred `notes.md` two-way sync feature.**
   Removed the **Deferred features → "Two-way sync of `notes.md` between vault and repo"** entry. User decision (2026-06-19): `notes.md` is a user-owned topic note that agents read from the vault when needed; there is no demonstrated need for repo↔vault sync, so the feature is dropped rather than parked.

## Why safe

No skill or `AGENTS.md` cross-reference points at the ROADMAP "Known limitations § No citation gate" anchor — skills cite `AGENTS.md` § Verifier system for the revisit trigger. Historical logs that mention the old anchor are dated records and were left as-is.

## Not changed

- `AGENTS.md` § Verifier system (still the normative home for the asymmetry table + trigger).
- `experimenter` / `evaluator` agent-table rows in ROADMAP (already say "no citation gate").
- Skill files (`ml-experiment-design`, `ml-evaluation`, `experimenter`) — gate logic untouched.

## Next

`code-dir` resolution backfill (audit-first): check whether `coder` Stage-2 and `experimenter` read `vault_code_dir(slug)` without first resolving via `python -m tools.paths code-dir <slug>`, then add the instruction only where missing.
