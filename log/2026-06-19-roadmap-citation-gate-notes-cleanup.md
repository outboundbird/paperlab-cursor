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

## code-dir backfill (audit + fix, 2026-06-19)

Audited whether `coder` Stage 2 and `experimenter` read `vault_code_dir(slug)` without first resolving via `python -m tools.paths code-dir <slug>` (the out-of-workspace vault blind spot from the 2026-06-04 GENI fix).

**Finding — risk largely already handled:**

- `coder` Stage 2 resolves via `code-dir <slug>` before reading in **both** regimes. Component surgery (`coder.md`, `ml-experiment-code` § component-surgery process) already spelled out the rationale ("vault is outside the workspace"); the **extension regime** gave the resolve instruction but omitted that rationale sentence.
- `experimenter` has **no blind spot** — it never reads vault code. Plan phase explicitly forbids reading `method.py` / code blocks (`experimenter/SKILL.md`); Build phase delegates code to the `coder` and only resolves `exp-vault` / `exp-sandbox` / `spec.md`.

**Fix applied (consistency only, no behavior change):** appended the caveat *"Resolve vault paths via the CLI before reading — the vault is outside the workspace."* to the two extension-regime resolve-paths steps:

- `.cursor/agents/coder.md` — extension-regime process step 1.
- `.cursor/skills/ml-experiment-code/SKILL.md` — extension-regime process step 1.

**ROADMAP:** flipped the Known-limitations "Residual risk" bullet to **resolved 2026-06-19** (both coder regimes covered; experimenter doesn't read vault code).

## arXiv MCP parked (2026-06-19)

User decision: park the thin `arxiv` MCP. `firecrawl` + the citation-verifier's arXiv/Crossref resolvers cover current needs and there is no demonstrated problem. ROADMAP § External-data access updated (conditional → parked) and a new entry added under § Parked with the revisit trigger (recurring need for structured arXiv metadata) and a scope guard (metadata lookup only, not a crawler).

## Planned-units cleanup (2026-06-19)

Trimmed `## Planned units` so it holds only forward-looking work; shipped detail now lives in dated logs / `changelog_history.md` / the Agents table.

- **§1 Experimenter suite** collapsed to a one-line "shipped 2026-06-17" unit that keeps the single open item (**A2** production-flow smoke). Removed the interaction-model / flow / data-design / file-layout / smoke-gate bullets (all shipped, all in logs).
- **§2 External-data access** removed entirely — `firecrawl` (done), `external-fetch-budget` (shipped 2026-06-18, in its log + "what's working"), `arxiv` (parked, in § Parked). A one-line note in the section intro records the graduation.
- **§3 `tools.reindex`** renumbered to §2; v1 prose collapsed to one line pointing at the changelog. Kept the forward-looking v2a–v2d directions and the two-memory critic loop verbatim.

## Schema candidates → changelog + fresh changelog entry (2026-06-19)

Both previously-offered extras applied:

- **Moved the two shipped `## Schema improvement candidates`** entries (gating-hypothesis `[GATED-OFF]` rule, table-cell tagging convention — both shipped 2026-06-18) out of `ROADMAP.md` into `changelog_history.md`. The ROADMAP section now carries a one-line "none currently open" placeholder so the structure remains for future candidates.
- **Added a fresh `changelog_history.md` entry** "Recently completed (2026-06-04 → 2026-06-18, experimenter suite completion + schema refinements)" above the 2026-06-02 entry: `coder` Stage 1 + Stage 2 (both regimes) + smoke gate, `critic` code-review split + extension-fidelity, `evaluator`, `experimenter` skill/command + Build-evaluate, `external-fetch-budget` rule, the LaTeX-only gate decision, and the two `ml-evaluation` schema refinements. The changelog's newest entry was stale at 2026-06-02.
