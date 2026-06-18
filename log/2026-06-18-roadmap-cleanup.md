# 2026-06-18 — ROADMAP cleanup

Trimmed `ROADMAP.md` of shipped-status text that duplicated the
Agents table or that was already covered in dated logs. The roadmap
is forward-looking; shipped narrative belongs in the dated logs.

No content preserved to `log/changelog_history.md` — the dated logs
in `log/` already document each shipped piece in more detail than
the deleted bullets did, and `git log -p ROADMAP.md` recovers any
literal wording if needed.

## What was removed

### § Planned units → §1 Experimenter suite

Replaced the 13-bullet block (≈ 30 lines) with a 6-bullet block
(≈ 12 lines). Removed:

- The "Four agents" sub-bullets (`experimenter`, `comparator`,
  `coder`, `evaluator`). Each duplicated its row in the Agents
  table at the top of the file.
- "Path helpers shipped this session" (`repo_experiments_dir` /
  `vault_experiments_dir` in `tools/paths.py`).
- "`.gitignore` carve-out shipped" (`sandbox/experiments/`
  re-included).
- "Blueprint bridge (designed 2026-06-03)" — fully covered by
  `log/2026-06-03-implementer-coder-blueprint-design.md` and
  `log/2026-06-04-codemap-from-coder-critic-audit.md`.
- "Build order" sequence with 5 ✅-marked completed milestones —
  replaced with a single "Remaining work: A2" pointer.
- "Experimenter conversational rewrite (shipped 2026-06-09;
  smoke-validated 2026-06-15/16)" — 13-line narrative covered by
  `log/2026-06-09-experimenter-conversational-rewrite.md` and the
  three 2026-06-15/16/17 logs.

Kept (genuinely forward-looking):

- Interaction-model summary (Model 3 hybrid).
- The flow diagram.
- Interactive data-design phase description.
- File-layout convention.
- "Parked sub-decision: a `coder` verifier gate" (still parked).
- New "Remaining work: A2" pointer.

### § Planned units → §3 reindex

Removed:

- "First run (2026-06-02): 45 nodes / 31 edges over the legacy test
  vault" paragraph — historical, covered by
  `log/2026-06-02-graph-groundwork-reindex-experimenter.md`.

Kept:

- v1 description, three resolved questions, "Why tool, not
  subagent?", v2a–v2d directions.

Condensed:

- "Two-memory critic loop → Partially realized (2026-06-04)"
  sub-bullet (7 lines) folded into the parent bullet (1 sentence
  pointing at the Agents table for the four shipped gates).

### § Parked

Removed:

- "`comparator` subagent + `ml-comparison` skill — UN-PARKED
  2026-05-29" subsection (8 lines including original framing).
  Comparator is shipped and in the Agents table; the un-parking is
  recorded in `log/2026-05-29-experimenter-design.md`.

Replaced the empty section with a one-line note: *"No items
currently parked — the previously-parked `comparator` was un-parked
and shipped 2026-05-29."* Keeps the section header so future parked
items have a home.

## What was kept untouched

- Agents table at the top — the canonical per-agent status.
- File layout contract.
- Decision framework (agent vs. skill vs. rule vs. hook vs. MCP).
- §2 External-data access — not shipped.
- §3 reindex v2a–v2d directions.
- § Exported to a separate project — visualizer reference.
- § Deferred features.
- § Known limitations (today's "No citation gate on
  `design.md` / `findings.md`" entry already added earlier today).
- § Schema improvement candidates — kept today's two
  shipped-2026-06-18 entries visible for now (will move out in a
  later cleanup pass).
- § Reference: what's currently working.

## Net effect

`ROADMAP.md` shrank by 22 lines net (30 removed, 8 added). Forward-looking content
(Agents table, Planned units' remaining work, v2 directions,
Deferred / Known limitations / Schema improvement candidates) is
now the bulk of the file. Shipped narrative lives only in dated
logs.

## Next step (unchanged)

A2 — production-flow re-validation of the full `/experimenter` loop
from a fresh chat on the `gib-importance` topic.
