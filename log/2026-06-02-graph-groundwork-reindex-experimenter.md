# 2026-06-02 — Graph-index groundwork + reindex v1 + experimenter shell

Paste the block at the bottom into a fresh chat to resume cleanly
without re-deriving today's decisions.

## What shipped today

Three connected pieces, plus a long design discussion that motivated
them. Committed in two commits (`4d94204` groundwork, `f607fde` reindex);
the experimenter shell is committed alongside this log.

### Design discussion (no code) — why this work exists

Reviewed the system's architectural weaknesses. The through-line: the
design leans on **convention enforced by prose** (skills, rules,
`AGENTS.md`) rather than **invariants enforced by code**. Six gaps
identified; user agreed with 1–5, partially with 6:

1. No dependency graph / index over artifacts.
2. No workflow state machine (lifecycle is implicit in which files exist).
3. No feedback/correction channel.
4. No evaluation of the system's own output quality.
5. No cross-paper / knowledge-base structure.
6. No shared ingestion layer — **user's refinement:** wants *two*
   representations, split by role: **generators** (`dissector`, `tutor`,
   `implementer`, `coder`, `explainer`) share one semantic working
   memory; **critics** (`critic`, verifiers, `evaluator`) hold a
   *different*, independently-derived representation so they can evaluate
   generator output. This is a generator/discriminator split — evaluation
   independence comes from the critic NOT sharing the generator's latent
   state. Generalizes the existing `citation-verifier` isolation into a
   principle.

Key locked design decisions for the future build (not all built yet):

- **Two firewalled memories** (generator working memory + critic
  consequence-lists). Critic runs **pre-emission** on the working memory
  (before any artifact is written) → retry ×2 → **escalate to user** if
  unresolved. No disk write/rewrite loop. Mirrors the dissector's inline
  LaTeX gate, generalized.
- **Critic checks "consequence lists"** — checkable consequences that
  must hold *if* the extraction is correct (limits, signs, types/shapes,
  invariants, Markov/independence, monotonicity), NOT semantic
  similarity (which the user rejected as arbitrary). Independence via
  complementary representation, not external oracle (none exists for
  method semantics) — a strong *consistency* net, partial correctness.
- **Graph index** is a derived sidecar built FROM the markdown; markdown
  stays source of truth. Per-artifact front-matter = truth; the index =
  derived rollup.
- **Build infrastructure now, connect later:** richer YAML + wiki-links
  now (cheap, reversible); the reader (`reindex`) and the critic loop
  later.

### 1. Graph-index front-matter groundwork (Phase 1) — commit `4d94204`

- Added `status`, `sources`, `concepts` keys to the artifact front-matter
  schema in `AGENTS.md` ("Graph index groundwork" subsection): inert
  today, double as Obsidian backlinks, become graph edges when `reindex`
  reads them. Prose-enforced until then (partial adoption expected).
- Propagated the schema to the six generator skills (`ml-paper-spec`,
  `ml-code-map`, `ml-tutor`, `ml-explanation`, `ml-synthesis`,
  `ml-comparison`). `tutor_log.md` carries only `status` (append-only
  header can't track per-turn edges).
- Created `.cursor/skills/concept-vocabulary.md` — grow-on-demand
  canonical concept list (avoids `IB` vs `Information Bottleneck` drift).
- `status` vocabulary: per-paper pipeline `acquired` → `dissected` →
  `implemented` → `critiqued` → `tutored`; multi-paper `compared`
  (comparator), `designed` (experimenter), `evaluated` (findings).
  **User correction:** comparator is NOT in the linear pipeline → its
  own `compared` value, not `critiqued`.

Decisions (locked with user): index at `vault/PaperLab/.index/`
(dotfolder, hides from Obsidian); concept vocab grown on demand; vocab
home `.cursor/skills/concept-vocabulary.md`; new fields go in skill
output schemas (uniform emission). Test papers in the vault deliberately
**not backfilled** (they were throwaway test data).

### 2. `tools.reindex` v1 — commit `f607fde`

- `tools/reindex.py` — deterministic read-only parser. Walks the vault,
  parses front-matter + body `[[wiki-links]]`, emits `graph.json` under
  `vault_index_dir()` (`<vault>/.index/`). Nodes: papers / topics /
  artifacts / concepts. Edges: `has_artifact`, `includes_paper`,
  `has_status`, `derived_from` (from `sources`), `mentions` (from
  `concepts` + bare body wiki-links). Drift report to stderr (missing
  schema keys, unknown concepts, unresolved `sources`). CLI:
  `python -m tools.reindex [--check]`.
- Added `vault_index_dir()` to `tools/paths.py` + `index-dir` CLI verb.
- **3 design Qs resolved:** (a) link-only edges, NO staleness hashing
  (needs write-side stamp → v2a); (b) concept normalization report-only,
  never rename; (c) JSON only, no `_index.md` rollup.
- **First run:** 45 nodes / 31 edges over the legacy vault. Only
  `has_artifact` fired — test papers predate the schema (expected; not
  backfilled). Parser verified working.
- **v2 directions (need more papers to validate):** v2a staleness
  (write-side hash stamp), v2b agents consult the graph, v2c lifecycle
  queries, v2d `_index.md` rollup, + the two-memory critic loop. All in
  `ROADMAP.md` §5.

### 3. `experimenter` design-phase shell (scope A)

- `.cursor/agents/experimenter.md` + `.cursor/skills/ml-experiment-design/SKILL.md`.
  Second agent of the Experimenter suite (after `comparator`).
- **Scope A — design phase ONLY.** Conversational design ⇄ user
  (criterion → methods → hypotheses → data design → MVP → rationale),
  one decision at a time. Invokes backend `comparator` for conceptual
  trade-offs. Writes `design.md` (`status: designed`, 7-section schema)
  with an inline LaTeX + citation gate (experiments/ tree skips the
  post-hoc hook). **Stops at the implement boundary** — `coder` /
  `evaluator` not built, so no code, no runs, no `findings.md`.
- **Critic advisory included** (un-parks §12 of the design log): consult
  a paper's `critic_reviews.md` during design **if present**, never
  force, never gate.
- **`findings.md` schema documented** in the skill but write-path
  deferred to the `evaluator`.
- **Seam A:** experimenter owns the data-synthesis *design*; the `coder`
  (future) implements it.

## Conversation rules in effect this session

The user set working rules: concise replies; list choices as text (no
multiple-choice popups); **no action without approval**; discuss before
building; git commits one-line < 10 words, no broken quotes, only when
asked. Honored throughout (each build phase gated on explicit user OK).

## Files touched

- `AGENTS.md` — front-matter schema (+ `status`/`sources`/`concepts`,
  graph groundwork), experimenter suite status, skill mapping,
  `agent: experimenter`, status values.
- `ROADMAP.md` — Planned unit §5 (`tools.reindex` + v2), Agents table
  (experimenter), build order, "Recently completed (2026-06-02)".
- `.cursor/skills/` — six generator skills (front-matter), NEW
  `concept-vocabulary.md`, NEW `ml-experiment-design/SKILL.md`.
- `.cursor/agents/experimenter.md` — NEW.
- `tools/paths.py` — `vault_index_dir()` + CLI verb.
- `tools/reindex.py` — NEW.

## Still pending / next

- `experimenter` is testable today (`/experimenter <topic>`); design
  phase + `comparator` work end-to-end. Not yet smoke-tested on a real
  topic.
- Next in suite: `coder` (backend scaffold + run, Seam B user-check
  gate), then `evaluator` (empirical interpretation, writes `findings.md`).
- `reindex` v2 (esp. v2a staleness) and the two-memory critic loop both
  want a larger real-paper corpus before building.

```text
HANDOFF — 2026-06-02 graph groundwork + reindex v1 + experimenter shell

CONTEXT
PaperLab gained graph-index groundwork, a reindex tool, and the
experimenter design-phase shell. Motivated by an architecture review:
system leans on prose-enforced convention over code-enforced invariants.

SHIPPED + COMMITTED
1. Front-matter groundwork (commit 4d94204): status/sources/concepts keys
   in AGENTS.md schema + 6 generator skills; concept-vocabulary.md (NEW,
   grow-on-demand). status vocab: acquired/dissected/implemented/
   critiqued/tutored (per-paper) + compared/designed/evaluated (suite).
   Keys inert until reindex reads them; double as Obsidian backlinks.
2. tools.reindex v1 (commit f607fde): read-only vault parser -> graph.json
   at vault_index_dir() (<vault>/.index/). Nodes papers/topics/artifacts/
   concepts; edges has_artifact/includes_paper/has_status/derived_from/
   mentions. CLI: python -m tools.reindex [--check]. Resolved: link-only
   (no staleness hash), concept drift report-only, JSON only. First run
   45 nodes/31 edges; only has_artifact fired (legacy papers predate
   schema, deliberately NOT backfilled). vault_index_dir() added to paths.
3. experimenter shell (committed w/ this log): .cursor/agents/experimenter.md
   + .cursor/skills/ml-experiment-design/SKILL.md. Scope A = DESIGN PHASE
   ONLY. design.md 7-section schema (status: designed) + inline LaTeX/
   citation gate. Invokes comparator (backend) for trade-offs. Critic
   advisory (consult critic_reviews.md if present, never force) — unparks
   design-log §12. findings.md schema documented, write deferred to
   evaluator. Stops at implement boundary (coder/evaluator unbuilt).

KEY DESIGN (locked, mostly NOT built yet)
- Two firewalled memories: generators share semantic working memory;
  critics hold INDEPENDENT complementary representation (consequence
  lists: limits/signs/types/invariants/Markov/monotonicity — NOT semantic
  similarity). Critic runs PRE-EMISSION on working memory -> retry x2 ->
  escalate to user. No disk write/rewrite loop. Generalizes dissector's
  inline gate + citation-verifier isolation.
- Graph index = derived sidecar built FROM markdown; markdown stays truth.
- Build infra now (YAML + wiki-links), connect later (reindex + critic loop).

BUILD ORDER (experimenter suite)
comparator (done) -> experimenter shell (done 2026-06-02) -> coder ->
evaluator.

NEXT
- Smoke-test /experimenter on a real topic.
- coder + evaluator (backend agents) to complete the suite + enable
  findings.md.
- reindex v2 (v2a staleness via write-side hash stamp; v2b graph-consulting
  agents; v2c lifecycle queries; v2d rollup) + two-memory critic loop:
  defer until a larger real-paper corpus exists.

WORKING RULES (user)
Concise; choices as text not popups; no action without approval; discuss
before build; commits one-line <10 words, no broken quotes, ask first.
```
