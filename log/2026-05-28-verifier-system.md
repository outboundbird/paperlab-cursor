# 2026-05-28 — Verifier system shipped

Context handoff from chat `b0903532-ab04-4619-9d56-42f2c741a326`.
Paste the block below into a fresh chat to resume cleanly without
re-deriving today's decisions.

## What shipped today (end-to-end verifier system)

Seven commits on `main`, **pushed**:

| Commit | Description |
|---|---|
| `4e7cdf0` | document live-test results + verifier scope boundaries |
| `0a420e7` | require unix-timestamp suffix on verifier temp files |
| `12e6c5a` | enable firecrawl plugin for citation verifier fallback |
| `bca296e` | extend post-hoc hook with citation verifier + document verifier system |
| `a8f941d` | add citation-verifier subagent + ml-citation-verify skill + R11 inline gate |
| `72f5b12` | add tools/verify_citations.py: arXiv + Crossref + firecrawl citation verifier |

(Earlier today, the LaTeX side: tool, skill+agent, R10 gate, hook,
`agent:` front-matter field — already on `main` from prior session.)

## Architecture

Two read-only backend subagents (`latex-verifier`,
`citation-verifier`) wrapping pure-Python tools, invoked via two
paths:

1. **Inline gate** (Tutor R10/R11, Explainer §3.5/§3.6) — pre-emission,
   sequential LaTeX → citations, separate retry budgets (max 2 each).
2. **Post-hoc hook** (`tools/hooks/verify_on_vault_write.py`) — on
   vault `.md` writes from non-gated agents; fails open, writes
   findings to vault `verifier_log.md`.

Citation tool detects arXiv IDs, DOIs, bare URLs. Three-tier
resolver: arXiv Atom API → Crossref REST → firecrawl CLI fallback.
Per-paper cache at `papers/<slug>/.cache/citations/`. Only
`mismatched` fails the gate; `unresolved` is a warning (transient
resolver issues are common).

## Live test results (`/tutor GIB`)

- **LaTeX gate**: fired correctly.
- **Citation gate**: skipped (no arXiv/DOI/URL — book citation, out
  of scope by design).
- **One drift caught + fixed**: Tutor improvised
  `.tmp_latex_verify_notes.md` instead of `_<unix_timestamp>.md`.
  Hardened in `0a420e7` with normative "MUST" clause + named
  anti-pattern in both verifier subagent files.

## Still deferred

1. Cache clearing at Tutor session end (currently survives sessions;
   manual `rm -rf papers/<slug>/.cache/` clears it).
2. KaTeX strict-mode renderer for LaTeX v2 (Linux machine task).
3. Other planned units in `ROADMAP.md` (`prerequisite`,
   `experimenter` subagents).

## Key files for orientation

- `tools/verify_latex.py`, `tools/verify_citations.py` — tools.
- `tools/paths.py` — has `firecrawl_cli()` helper for Windows-scoop
  PATH resolution.
- `tools/hooks/verify_on_vault_write.py` — post-hoc hook.
- `.cursor/skills/ml-latex-verify/SKILL.md`,
  `.cursor/skills/ml-citation-verify/SKILL.md` — schemas.
- `.cursor/agents/latex-verifier.md`,
  `.cursor/agents/citation-verifier.md` — subagents.
- `.cursor/skills/ml-tutor/SKILL.md` §§ R10–R11 — inline gates.
- `AGENTS.md` § "Verifier system" — architecture overview.

## Project quirks (Windows / corporate env)

- Vault path must be ASCII (no emoji) up to `PaperLab/` segment.
- firecrawl CLI not on `PATH`; resolved via `firecrawl_cli()` helper
  to `%USERPROFILE%/scoop/persist/nodejs/bin/firecrawl.cmd`.
- Zscaler proxy can produce 403s on installs and `unresolved` on
  citations — that's why `unresolved` is a warning, not a failure.

## Interaction style (carry over)

- User wants concise responses; no unsolicited actions.
- Discuss design before building when there are real forks.
- Review own work between steps; flag real bugs, don't redo
  perfect.
- Commits split sensibly, one-line lowercase verb-led messages.

## Handoff block (paste this into a fresh chat)

```
Context handoff from chat b0903532-... — 2026-05-28

WHAT SHIPPED TODAY (verifier system, end-to-end)

Seven commits on main, pushed:
  4e7cdf0 document live-test results + verifier scope boundaries
  0a420e7 require unix-timestamp suffix on verifier temp files
  12e6c5a enable firecrawl plugin for citation verifier fallback
  bca296e extend post-hoc hook with citation verifier + document verifier system
  a8f941d add citation-verifier subagent + ml-citation-verify skill + R11 inline gate
  72f5b12 add tools/verify_citations.py: arXiv + Crossref + firecrawl citation verifier
(plus the earlier LaTeX commits from the prior session)

Architecture: two read-only backend subagents (latex-verifier,
citation-verifier) wrapping pure-Python tools, invoked via two paths:
  - Inline gate (Tutor R10/R11, Explainer §3.5/§3.6): pre-emission,
    sequential LaTeX→citations, separate retry budgets (max 2 each).
  - Post-hoc hook (tools/hooks/verify_on_vault_write.py): on vault
    .md writes from non-gated agents; fails open, writes findings to
    vault verifier_log.md.

Citation tool detects arXiv IDs, DOIs, bare URLs. Three-tier resolver:
arXiv Atom API → Crossref REST → firecrawl CLI fallback. Per-paper
cache at papers/<slug>/.cache/citations/. Only `mismatched` fails the
gate; `unresolved` is a warning (transient resolver issues common).

LIVE TEST RESULTS (/tutor GIB)
- LaTeX gate: fired correctly.
- Citation gate: skipped (no arXiv/DOI/URL — book citation, out of
  scope by design).
- One drift caught: Tutor improvised .tmp_latex_verify_notes.md
  instead of _<unix_timestamp>.md. Fixed in 0a420e7 with normative
  "MUST" clause + named anti-pattern.

STILL DEFERRED
1. Cache clearing at Tutor session end (currently survives sessions;
   manual rm -rf papers/<slug>/.cache/ clears it).
2. KaTeX strict-mode renderer for LaTeX v2 (Linux machine task).
3. Other planned units in ROADMAP.md (prerequisite, experimenter
   subagents).

KEY FILES (for orientation)
- tools/verify_latex.py, tools/verify_citations.py — tools
- tools/paths.py — has firecrawl_cli() helper for Windows-scoop PATH
- tools/hooks/verify_on_vault_write.py — post-hoc hook
- .cursor/skills/ml-{latex,citation}-verify/SKILL.md — schemas
- .cursor/agents/{latex,citation}-verifier.md — subagents
- .cursor/skills/ml-tutor/SKILL.md §§ R10–R11 — inline gates
- AGENTS.md § "Verifier system" — architecture overview

PROJECT QUIRKS (Windows / corporate env)
- Vault path must be ASCII (no emoji) up to PaperLab/ segment.
- firecrawl CLI not on PATH; resolved via firecrawl_cli() helper to
  %USERPROFILE%/scoop/persist/nodejs/bin/firecrawl.cmd.
- Zscaler proxy can produce 403s on installs and `unresolved` on
  citations — that's why unresolved is a warning, not a failure.

INTERACTION STYLE (carry over)
- User wants concise responses; no unsolicited actions.
- Discuss design before building when there are real forks.
- Review own work between steps; flag real bugs, don't redo perfect.
- Commits split sensibly, one-line lowercase verb-led messages.
```
