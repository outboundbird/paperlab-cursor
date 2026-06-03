# 2026-06-03 — Learning-suite rename, acquirer empty-folder fix, implementer/coder blueprint design

Design-only session (Ask mode for most of it). No code written. Three
threads: a naming convention, a small acquirer fix, and a substantial
implementer/coder architecture decision that bridges the Learning suite
and the Experimenter suite. Paste the block at the bottom into a fresh
chat to resume.

## 1. Naming — "Learning suite"

The five per-paper agents previously called the "core pipeline"
(`acquirer`, `dissector`, `implementer`, `critic`, `tutor`) are now the
**Learning suite**, paralleling the existing **Experimenter suite**
(`experimenter`, `comparator`, `coder`, `evaluator`). Documentation /
naming convention only — no code logic changes. Mirrors how the
per-paper `status` lifecycle (`acquired → dissected → implemented →
critiqued → tutored`) already groups these agents.

## 2. Acquirer fix — no empty `upstream/` or `supplementals/`

Current behavior leaves empty folders behind: `ml-acquisition` Item 4
creates `repo_supplementals_dir(slug)` *before* knowing if supplements
exist; the folder diagram implies an `upstream/` wrapper always appears
even when no repo is found/cloned.

**Fix (skill-prose only, no `tools/paths.py` change):** create each
folder **lazily** — only right before a successful write into it, never
as a precondition. `paper-info.md` rows read "— none / not created"
instead of pointing at an empty dir. The path helpers are unchanged;
they only return paths — the agent decides when to `mkdir`.

**Scope decision (user):** prevent *future* empty folders only. Do
**not** clean up existing empty folders (no `rerun` cleanup pass).

## 3. Implementer / coder — the blueprint bridge (the main work)

### Problem

The Experimenter suite must compare methods on the same dataset, which
means **code for each method must exist**. When a paper ships official
code, fine. When it doesn't, someone must write code from the paper's
math. Tension:

- **Implementer holds the math** (generator with paper-bound working
  memory: concepts, equations, spec↔code correspondence) but is
  strictly **read-only / clone-dependent** today (`ml-code-map`: "does
  not execute upstream code … or produce new Python files"). Its
  credibility rests on "this is the *real* official code."
- **Coder holds the execution** (scaffolds runnable code into
  `sandbox/experiments/<topic>/`, with the run gate) but has **no paper
  working memory** — it would re-derive math from `spec.md` cold.

Naive options both break something: implementer-writes-code violates its
read-only generator contract; coder-writes-from-scratch is lossy and
duplicates the implementer's job.

### Resolving idea — separate *what to build* from *who builds it*

**Implementer emits an implementation *blueprint* (a contract, not
runnable code); coder consumes it to write runnable code.** Working
memory transfers **through an inspectable markdown artifact**, not
shared live state — consistent with the firewalled-memory principle and
the existing tutor/explainer, experimenter/coder splits.

### Locked decisions

- **`code_blueprint.md` is a separate file** (NOT a section in
  `code_map.md`). Rationale (user): keep the official-vs-reconstructed
  distinction visible — if `code_map.md` exists, official code exists;
  if `code_blueprint.md` exists, it was reconstructed from math. Merging
  them would hide whether the paper shipped real code.
- **Framework-agnostic** blueprint (math → shapes → ordered steps →
  invariants), more reusable than pre-targeting one framework.
- **Lazy** — written only when **no official code** is available. The
  earlier "no-code implementer" question resolves as: **Path 1**
  (implementer stays read-only on official code → `code_map.md`)
  **plus** this blueprint mode for the from-math case. Path 3
  (delegation to coder) happens **through the artifact**, not a live
  handoff.
- **Owner is the `implementer`**, not the explainer (explainer = tutor's
  concept-prose backend). Implementer holds the spec↔code working
  memory, so it is the natural blueprint owner.

### Two-hop fidelity model

```
paper math → [implementer] → code_blueprint.md → [coder] → runnable code
             (hop 1)                              (hop 2)
```

- **Hop 1 (paper math → blueprint):** guarded by the **critic running
  pre-emission**, using its **own independent** derivation of the paper
  (NOT the implementer's working memory — the firewall). Retry ×2 →
  escalate to user. Draft blueprint passed **as payload in the
  invocation** (tutor/explainer-style inline gate), checked before any
  disk write; written to `code_blueprint.md` only on PASS. No disk
  write/rewrite loop. Same `critic` *agent/role* gains a blueprint mode,
  but builds its **own** representation — "same critic" means same role,
  independent memory, never shared.
- **Hop 2 (blueprint → code):** guarded by **invariants-as-assertions**.
  The blueprint's required invariants section (shapes, signs, limits,
  monotonicity, row-stochasticity, etc. — the same "consequence lists"
  from the 2026-06-02 two-memory design) is emitted by the coder as
  **runtime assertions / shape checks** alongside the code, run on a
  synthetic input **before declaring done**. Assertion fail → code
  doesn't match the contract → fix or escalate. This turns "faithful to
  the blueprint" into a machine-checkable property and gives the coder's
  run gate concrete pass/fail criteria. Honest limitation: assertions
  prove the *stated* invariants hold, not that enough were listed —
  strong consistency, partial correctness (same stance as the two-memory
  design).

**User's sharpening:** the blueprint must be information-rich enough to
**minimize translation ambiguity** in hop 2 (pin axes, shapes, step
order, edge cases). A vague blueprint with weak invariants is the worst
case. "Be maximally specific" + "carry strong invariants" are the two
halves of hop-2 safety.

### Coder — two modes keyed on which artifact exists

| Paper has official code? | Implementer writes | Coder reads | Coder's job |
|---|---|---|---|
| Yes | `code_map.md` | `code_map.md` + upstream repo | **Adapt/wrap** real code to harness (mostly plumbing; fidelity inherited from authors) |
| No | `code_blueprint.md` | `code_blueprint.md` | **Generate + assert** against invariants |

- **Official-code path uses import in place** (user decision): import the
  method from `repo_upstream_dir(slug)` rather than vendoring a copy into
  the experiment folder. Lighter; experiment stays pinned to the recorded
  clone commit. Trade-off accepted: re-pulling the clone can shift the
  experiment (commit SHA already tracked).
- The artifacts the implementer produces **tell coder which mode to use**
  — a clean seam parallel to the implementer's own branch.

### Harness interface (design-time concept)

The **harness** is the experiment scaffolding (loads dataset, loops over
methods, calls each, collects results, computes metrics). The
**interface** is the common "plug" every method must fit — e.g. a class
with `fit(X_train, Y_train)` and `predict(X_test) -> Y_pred` of a fixed
shape, plus dataset format and metric calls. Internals differ per
method; the plug is fixed, so the harness runs all methods identically →
fair comparison.

**Decision (user): owned at design time, recorded in `design.md`.** You
cannot fairly compare methods until the common plug is defined, so it
belongs in the experimenter's design phase. Both adapted official code
and blueprint-built code must conform to it.

### Worked example (for intuition)

Topic: compare two attention variants. Method A has official code →
coder imports `OfficialAttnModel` in place and wraps it to `fit/predict`.
Method B has no code → implementer writes a blueprint pinning
`A = softmax(S, over LAST axis)`, shape `[N,L,L]`, invariants
"rows sum to 1, entries ≥ 0"; coder emits those as `assert`s and runs on
synthetic input. A `dim=0` mistake fails the row-sum assertion before
the experiment runs → hop-2 drift caught automatically. The harness
loops over both as `fit/predict` objects, blind to their origin.

## Design-phase invocation (clarified)

`/experimenter <topic>` (new or resume), `/experimenter` (resume most
recent), or natural language. Invoking opens the interactive session;
the design phase **is** that session — there is no separate "enter design
phase" command. Confirmed against `.cursor/agents/experimenter.md`.

## Build order (this work)

1. **Blueprint schema + implementer blueprint mode** — defines
   `code_blueprint.md` format incl. the **required invariants section**,
   and the implementer's no-code branch that drafts it in working memory.
   Lands first because the critic can't be tested without a real
   blueprint to run against.
2. **Critic blueprint mode** — pre-emission gate: independent
   re-derivation → check draft (as payload) → retry ×2 → escalate →
   write on PASS. Design the schema's invariants and the critic's checks
   **together** (generator vs. discriminator views of one contract), even
   though the schema is built first.
3. **(later)** coder's two modes (import/adapt vs. generate+assert) +
   harness interface; then evaluator.

Hop-1 critic is the priority guard (drift at the entry point poisons
everything downstream), but its build depends on the blueprint artifact
existing — hence schema-first, critic-second.

## Open / not yet decided

- Whether the blueprint schema lives in `ml-code-map` or a new
  `ml-blueprint` skill.
- Whether the critic blueprint mode lives in `ml-critique` or its own
  skill; `critic_reviews.md` vs. a separate output for blueprint audits.
- Coder/harness specifics (the §3 "later" items) — deferred until the
  blueprint + critic land.

## Files touched

None this session — design only.

```text
HANDOFF — 2026-06-03 Learning-suite rename + acquirer fix + implementer/coder blueprint

CONTEXT
Design-only session. Bridges the Learning suite (per-paper agents) and the
Experimenter suite: how to get runnable method code when a paper ships no
official code, without breaking the implementer's read-only generator
contract or the firewalled generator/critic memory principle (2026-06-02).

SETTLED
1. Rename "core pipeline" -> "Learning suite" (acquirer, dissector,
   implementer, critic, tutor). Doc/naming only.
2. Acquirer: create upstream/ and supplementals/ LAZILY (only before a
   successful write); never as a precondition. Prevent FUTURE empties only,
   no cleanup of existing. Skill-prose change to ml-acquisition; no paths.py
   change.
3. Implementer/coder blueprint bridge:
   - Implementer emits code_blueprint.md (separate file, NOT in code_map.md,
     so official-vs-reconstructed stays visible). Framework-agnostic,
     info-rich, REQUIRED invariants section. Written LAZILY only when no
     official code. Implementer owns it (holds spec<->code memory).
   - No-code question resolved: Path 1 (read-only on official code ->
     code_map.md) + blueprint mode for from-math case. Delegation to coder
     happens THROUGH the artifact.
   - Two hops: paper->blueprint (hop1) guarded by CRITIC pre-emission with
     its OWN independent paper memory (firewall; same critic ROLE, not
     shared memory), draft passed as PAYLOAD (tutor/explainer-style inline
     gate), retry x2 -> escalate, write on PASS, no disk rewrite loop.
     blueprint->code (hop2) guarded by invariants-as-assertions: coder emits
     blueprint invariants as runtime asserts + runs on synthetic input
     before done. Strong consistency, partial correctness.
   - Blueprint must minimize translation ambiguity (pin axes/shapes/order).
   - Coder TWO modes keyed on which artifact exists: official -> IMPORT IN
     PLACE from upstream/ + wrap to harness; no-code -> generate+assert.
   - Harness interface = common plug (fit/predict + shapes, dataset format,
     metrics) all methods conform to; owned at DESIGN TIME in design.md.

BUILD ORDER
1) blueprint schema + implementer blueprint mode (schema first so a real
   blueprint exists to test against).
2) critic blueprint mode (pre-emission gate; design invariants+checks
   together).
3) later: coder two modes + harness; evaluator.

OPEN
- blueprint schema home: ml-code-map vs new ml-blueprint skill.
- critic blueprint mode home: ml-critique vs own skill; output file.
- coder/harness specifics deferred.

WORKING RULES (user)
Concise; choices as text not popups; no action without approval; discuss
before build; commits one-line <10 words, no broken quotes, ask first.
```
