# 2026-06-03 — Two-stage coder design (standalone per-paper + experiment adapt-mode)

Design-only session (Ask mode). No code written. Follows the same-day
implementer/coder blueprint design
([`log/2026-06-03-implementer-coder-blueprint-design.md`](./2026-06-03-implementer-coder-blueprint-design.md));
this log revises the **coder** half of that design before it is built.
Build deferred to a later session. Paste the block at the bottom into a
fresh chat to resume.

## Trigger

Smoke-tested implementer blueprint mode on GENI — it produced a strong
`code_blueprint.md` (well-pinned axes, thorough §4 invariants). Natural
next step was "use the coder to code it," which surfaced that the
`coder` is unbuilt **and** that its original single-stage,
experiment-scoped design did not fit the user's intent.

## The revision — split the coder into two stages

The original design (2026-06-03 blueprint log) had a single backend-only
`coder` that regenerated method code **per experiment** inside
`sandbox/experiments/<topic>/methods/<slug>/`. The user proposed
splitting it so paper-method code is written **once per paper** and
**reused** across experiments:

```
blueprint (or official code)
        ↓  Stage 1 — standalone per-paper coder
   runnable, invariant-validated method code in the VAULT (<vault>/<slug>/)
        ↓  Stage 2 — coder adapt-mode (invoked by experimenter)
   wrapped to the topic harness in sandbox/experiments/<topic>/methods/<slug>/
```

### Why this is a net win

- **Reuse:** a method coded once appears in many experiments without
  re-deriving code (original design regenerated per-topic — wasteful and
  a repeated hop-2 fidelity risk).
- **Two source branches converge.** At experiment time both look
  identical — "take paper-bound code, wrap to harness":

  | | Paper-bound code | Experiment adaptation |
  |---|---|---|
  | Official code | `upstream/<slug>/` (clone) | wrap to harness |
  | No code | `<vault>/<slug>/` (Stage-1 coder) | wrap to harness |

  Stage 1 produces the no-code equivalent of a clone.
- **Hop-2 validated once, in isolation** — invariants-as-assertions run
  in a clean per-paper context, not entangled with harness plumbing.
  This *is* the standalone GENI hop-2 smoke test.
- **Fits the existing seam/firewall philosophy** — paper-bound knowledge
  (method code) lives with the paper; experiment glue (harness
  conformance) lives with the experiment.

## Settled decisions

1. **Two-stage split** — Stage 1 (standalone, per-paper, user-invokable)
   + Stage 2 (coder adapt-mode, invoked by experimenter).
2. **Stage-1 code lives in the VAULT** (`<vault>/<slug>/`), not
   `sandbox/`. Rationale: user reviews it; the vault is git-tracked.
   **⚠️ Contract change:** this crosses the current "code in the repo,
   generated notes in the vault" split (ROADMAP "File layout contract").
   Runnable `.py` in the vault is new — must be made consciously;
   affects `tools/paths.py` helpers, the regenerate-prompt rule, and the
   post-hoc verifier hook (which currently expects `.md` under
   `<slug>/`). Resolve the implications at build time.
3. **Coder does all coding** (generate in Stage 1, adapt in Stage 2);
   **experimenter only coordinates** — never writes code. Tightens
   Seam A: experimenter owns design + invocation, coder owns all code.
4. **Hybrid interface (Stage 1 output).** Method coded **paper-natural**
   in its guts and naming (faithful to the blueprint, readable for user
   review), **plus** a thin, documented entry-point contract (a `Method`
   wrapper with declared I/O) so the coder's Stage-2 adapt-mode always
   starts from a known handle instead of re-reading each bespoke
   implementation.
   - Rejected **pure conventional** (`fit`/`predict` everywhere): forces
     a supervised-learner mold onto methods that are not learners
     (simulators, closed-form centrality). GENI fits `fit/predict`, but
     the convention must not assume every method does.
   - Rejected **pure paper-natural**: fine for faithfulness, but
     adapt-mode would reverse-engineer a bespoke signature every time.
   - Hybrid = faithful inside, predictable at the boundary.
5. **GENI smoke test = Stage 1**, once Stage 1 exists: blueprint →
   `<vault>/GENI/` code → validate §4 invariants. No harness needed.

## Open items (resolve at build time)

- Exact vault filenames/layout for Stage-1 code (single
  `code_<slug>.py`? a subfolder? multiple files allowed?).
- The hybrid `Method` interface contract spec — what the wrapper must
  expose (constructor, entry point, declared input/output contract).
- New skill `ml-experiment-code` for the coder: one skill covering both
  stages, or split into two.
- Confirm hybrid handles non-learner methods (simulators, closed-form)
  without forcing `fit`/`predict`.
- `tools/paths.py` helper for the Stage-1 vault code path.
- Does Stage 1 need its own verifier gate, or are the
  invariants-as-assertions self-sufficient as the hop-2 guard?
- Post-hoc verifier hook: currently fires on `.md` writes under
  `<slug>/`; decide whether it should ignore `.py`, or whether Stage-1
  code needs any hook treatment.

## Open items — RESOLVED 2026-06-04

All seven resolved with the user before building Stage 1:

1. **Vault Stage-1 code layout** — subfolder `<vault>/<slug>/code/`
   holding `method.py` (implementation), optional `test_invariants.py`
   (the §4 assertions), and optional `README.md`. **Multiple files
   allowed.** Keeps runnable code visually separate from the paper
   folder's markdown.
2. **Hybrid `Method` contract** — a class exposing: a constructor taking
   declared hyperparameters; **one** documented entry point
   (`run(inputs)` / `forward(inputs)`); and a contract block declaring
   input names + shapes and output name + shape, lifted from blueprint
   §2. Paper-natural names inside; the wrapper is the stable handle
   Stage-2 adapt-mode reads.
3. **`ml-experiment-code` skill** — **one** skill, two clearly-marked
   sections (Stage 1 generate, Stage 2 adapt). Must be written to avoid
   Stage 1/2 confusion. Mirrors `ml-code-map` + `DEEP_DIVE`.
4. **Non-learner methods** — the contract requires **only** constructor
   + entry point + I/O declaration. `fit`/`predict` are **optional**,
   added by a learner when natural, never forced. A simulator exposes
   `run(params) -> trajectory`; a closed-form method exposes
   `run(graph) -> scores`; both are fully compliant without
   `fit`/`predict`. (GENI is a learner, so the smoke test won't exercise
   the non-learner path, but the contract states it.)
5. **`tools/paths.py` helper** — add `vault_code_dir(slug)` returning
   `<vault>/<slug>/code/` + a CLI verb, consistent with `vault_path` /
   `vault_index_dir`. Nothing hard-codes the path.
6. **Stage-1 verifier gate** — **none for now.** The
   invariants-as-assertions are executable (run on synthetic input
   before done) and serve as the hop-2 guard; a separate critic-style
   gate would duplicate them. Revisit after the GENI smoke test if the
   asserts prove insufficient.
7. **Post-hoc verifier hook** — scope it to `.md`, **ignore `.py`.** The
   latex/citation verifiers are meaningless on code, so Stage-1 `.py`
   writes must not trigger the hook.

The contract change (runnable code in the vault) stays contained:
dedicated subfolder (#1), dedicated path helper (#5), hook scoped to
`.md` (#7).

## Stage 1 — BUILT + smoke-tested 2026-06-04

Built this session:

- `tools/paths.py` — `vault_code_dir(slug)` (`<vault>/<slug>/code/`) + the
  `code-dir` CLI verb.
- `.cursor/skills/ml-experiment-code/SKILL.md` — Stage-1 section fully
  specified (file layout, hybrid `Method` contract, process,
  invariants-as-assertions hop-2 guard, self-checks, scope); Stage-2
  section is a marked PLANNED placeholder.
- `.cursor/agents/coder.md` — Stage-1 user-invokable (`/coder code <slug>`),
  route detection (blueprint primary / official-code reimplementation),
  prerequisites, 3-attempt invariant fix budget; Stage-2 stubbed as
  not-built.
- `tools/hooks/verify_on_vault_write.py` — documented the deliberate
  `.py`-ignore (existing `.md`-only filter already covers it; no logic
  change needed).
- `AGENTS.md`, `ROADMAP.md`, `README.md` — updated to the two-stage
  design (coder spans both suites; vault `code/` documented as the one
  exception to the code-in-repo/notes-in-vault split).

### GENI smoke-test result (PASS)

Ran `/coder code GENI` (chat `1923966d-ed49-48a9-82d7-a6545e016167`). The
agent wrote `method.py`, `test_invariants.py`, and `README.md` to
`<vault>/GENI/code/`:

- `method.py` — one `Method(nn.Module)` with the I/O contract block,
  `forward` entry point, paper-natural names tied to blueprint §3.2–§3.6,
  and optional `fit`/`predict` (GENI is a learner). Faithful to the
  blueprint (predicate-aware score aggregation, head-average bridge,
  log-in-degree centrality, MSE-on-labeled loss).
- `test_invariants.py` — 12 test functions covering **24** §4 invariants
  (shapes, row-stochastic + non-negative attention, aggregation
  consistency, pre-aggregation-score dependence, head-average bridge,
  `s* >= 0`, `loss >= 0`, log-in-degree centrality, single-neighbor
  α = 1, softmax shift-invariance, final-head-average-before-ReLU, NDCG in
  `[0,1]`).

Independent run by hand (`python test_invariants.py`): **exit 0, all 12
PASS, "24 §4 invariants covered."** The hop-2 guard works end-to-end:
blueprint → vault code → invariants green. Stage 1 validated on a real
paper.

## Build order (next session)

1. (done this session) Capture this design log.
2. Resolve the open items (esp. vault-code layout + hybrid contract +
   the vault-code contract change).
3. Build **Stage 1**: standalone coder agent + `ml-experiment-code`
   skill (Stage-1 half). Unblocks the GENI hop-2 smoke test.
4. **GENI smoke test** (blueprint → vault code → validate invariants).
5. Build **Stage 2**: coder adapt-mode + harness wiring + experimenter
   invocation.
6. Update `AGENTS.md`, `ROADMAP.md`, README chart.

## Files touched

None this session — design only.

```text
HANDOFF — 2026-06-03 two-stage coder design

CONTEXT
Revises the coder half of the same-day implementer/coder blueprint design
BEFORE building it. Triggered by the GENI blueprint smoke test (implementer
blueprint mode works; produced a strong code_blueprint.md) and the question
"now use coder to code it" — coder is unbuilt and its original single-stage
experiment-scoped design didn't fit intent.

THE REVISION
Split coder into TWO stages:
- Stage 1 (NEW, standalone, per-paper, USER-invokable): blueprint or official
  code -> runnable, invariant-validated method code written to the VAULT
  (<vault>/<slug>/). Validates hop-2 (blueprint §4 invariants as runtime
  asserts on synthetic input). This IS the standalone GENI hop-2 smoke test.
- Stage 2 (coder adapt-mode, invoked by experimenter): wrap Stage-1 vault code
  to the topic harness -> sandbox/experiments/<topic>/methods/<slug>/.
Two source branches converge at experiment time: official code in upstream/ and
no-code in vault both become "paper-bound code -> wrap to harness."

SETTLED
1. Two-stage split.
2. Stage-1 code lives in the VAULT (git-tracked, user-reviewable). CONTRACT
   CHANGE: crosses "code in repo, notes in vault" split; affects paths.py,
   regenerate rule, post-hoc verifier hook (expects .md). Resolve at build.
3. Coder does ALL coding (generate + adapt); experimenter only coordinates.
4. HYBRID interface: paper-natural guts+naming + thin documented Method wrapper
   with declared I/O. Rejected pure-conventional (forces fit/predict on
   non-learners) and pure paper-natural (adapt-mode re-reads bespoke each time).
5. GENI smoke test = Stage 1 once it exists.

OPEN (resolve at build)
- vault Stage-1 code filenames/layout; hybrid Method contract spec; one vs two
  ml-experiment-code skills; non-learner methods under hybrid; paths.py helper
  for vault code; whether Stage 1 needs a verifier gate beyond the asserts;
  post-hoc hook behavior on .py.

BUILD ORDER (next session)
1) this log (done). 2) resolve open items. 3) Stage 1 coder agent +
ml-experiment-code skill (Stage-1 half) -> unblocks GENI. 4) GENI smoke test.
5) Stage 2 adapt-mode + experimenter wiring. 6) update AGENTS/ROADMAP/README.

WORKING RULES (user)
Concise; choices as text not popups; no action without approval; discuss
before build; commits one-line <10 words, no broken quotes, ask first.
```
