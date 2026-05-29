# 2026-05-29 — Experimenter suite design

Design session for the `experimenter` agent and its delegated
collaborators. **Design doc only** — no agent/skill files written yet.
This document is the source of truth for the build phase that follows.

## 1. Mission and scope

The `experimenter` helps the user **design, run, and interpret
empirical experiments that compare methods from multiple papers** the
user has read, on synthetic data tailored to a chosen criterion.

This is a deliberate re-scope of the roadmap's original single-paper
"toy implementation in `sandbox/<slug>/`" framing. The new framing is:

- **Multi-paper, multi-method.** A comparison can involve 3+ methods
  addressing the same *type of problem* — not a simple A-vs-B.
- **Problem-type-oriented**, not paper-oriented. The unit of work is a
  *problem class / comparison topic*, not one paper slug.
- **Full lifecycle:** design → synthesize data → implement → evaluate.
- **Collaborative ("help the user"),** not fire-and-forget. The
  experimenter is a pair-designer/advisor across phases, in the style
  of the `tutor`, not an autonomous scaffolder.

This re-scope absorbs the previously-parked `comparator` (un-parked and
sharpened here) and adds three new agents.

## 2. Architecture — four agents

| Agent | Mode | Role |
|---|---|---|
| `experimenter` | User-facing **orchestrator** | Holds the interactive session. Owns experiment design and the data-design *decisions*. Does small in-session code tweaks. Discusses results with the user. Invokes the three agents below. |
| `comparator` | **Dual** (user-facing + backend) | **Conceptual** method comparison from `spec.md` files (+ `code_map.md` when present). Prose output. Runs standalone ("compare these methods") or as a design-phase input the experimenter invokes. |
| `coder` | **Backend-only** | One-shot heavy scaffold: writes data-synthesis code and method implementations into `sandbox/experiments/<topic>/`, and runs experiments. Invoked by the experimenter. |
| `evaluator` | **Backend-only** | **Empirical** results interpretation (reads run outputs). Communicates only through the experimenter. |

### 2.1 Why this split — delegation rationale

The central design tension was **one-shot delegation vs. in-session
work**:

- A **delegated subagent is one-shot**: one prompt in, one report out.
  It starts fresh (does not see the chat history unless re-packed into
  its prompt), works autonomously with no mid-task user dialogue, and
  its context is discarded when it returns. To revise, you invoke it
  again and re-state context.
- **In-session** work is done by the agent that is talking to the user;
  it remembers the whole thread and iterates turn-by-turn.

A tight "write code → user checks → tweak → re-check" loop is clumsy
across one-shot boundaries (every tweak re-packs the code + design +
feedback, and the coder forgets prior rounds).

**Resolution — Model 3 (hybrid).** The `coder` does the *heavy initial
scaffold* one-shot (synth + method skeletons, the big first write). The
`experimenter` handles *small in-session tweaks* during the tight
review loop. This mirrors the existing **tutor/explainer** split, which
is already proven in this codebase: explainer (one-shot backend) writes
the heavy intermediate; tutor (in-session) refines and talks to the
user.

Rejected alternatives:
- *Model 1 (all delegated, standalone coder):* architecturally tidy but
  the iterative code loop is awkward one-shot.
- *Model 2 (experimenter codes everything in-session, no coder):* good
  loop ergonomics but bloats the experimenter and doesn't isolate the
  heavy scaffold.

### 2.2 Why two comparison agents (`comparator` vs. `evaluator`)

Conceptual and empirical comparison differ in input, timing, and
output enough to be separate agents:

| | `comparator` (conceptual) | `evaluator` (empirical) |
|---|---|---|
| Input | N papers' `spec.md` (+ `code_map.md`) | run outputs (metrics, logs) from the sandbox |
| Runs | design phase (before code) | evaluate phase (after runs) |
| Output | prose: method trade-offs, what differs | numbers/tables: who won, by how much |
| Judgment | literature synthesis | results interpretation |

`comparator`'s input comes purely from durable artifacts (specs), so it
is safely **dual-mode** (standalone *or* backend). `evaluator` needs run
outputs that only exist after an experiment, so it stays **backend-only**
and routes through the experimenter for now (standalone use deferred).

## 3. The flow

1. **Design.** `experimenter` ⇄ user. Establish the comparison topic,
   the criterion/situation to test, the method set, and the
   data-synthesis design.
2. **Method trade-offs (on demand).** When the user asks about the
   advantages of each method, `experimenter` invokes `comparator`
   (conceptual), which reads the relevant `spec.md` files and reports
   back; `experimenter` relays to the user.
3. **Implement + run.** Once the design is fixed, `experimenter`
   invokes `coder` to scaffold the data-synthesis code and method
   implementations. **User-check gate (Seam B):** the user reviews the
   written code *before* it is run. After approval, `coder` runs the
   experiment. `experimenter` handles small tweaks in-session.
4. **Evaluate.** When results are out, `experimenter` invokes
   `evaluator` to interpret them; `experimenter` discusses the findings
   with the user.

### 3.1 Seams

- **Seam A — data design vs. data code.** The *data-synthesis design
  decision* (what distribution, what stresses the criterion, synthetic
  vs. small real, metrics/baselines/seeds) stays with `experimenter` ⇄
  user. The `coder` owns *both* the data-synthesis code and the method
  code — it implements the agreed design, it does not decide it.
- **Seam B — user-check gate.** Between `coder`-writes and `coder`-runs
  the user reviews the code. Writing and running are not a single
  autonomous step.

### 3.2 Orchestration mechanics

The conversation always stays with `experimenter`. `comparator`,
`coder`, and `evaluator` are **bounded one-shot tasks** that report
back; they never hold a conversation with the user directly (the only
dual-mode exception is `comparator` when *the user* invokes it
standalone, in which case it is itself the responder for that one task).

## 4. File layout

Mirrors PaperLab's core split: **understanding/notes in the vault, code
and data in the repo.**

### 4.1 Vault — design notes and findings

```
<vault_paperlab_path>/experiments/<topic>/
├── design.md      experiment design: topic, criterion, method set,
│                  data-synthesis design, decision rationale
└── findings.md    evaluator/experimenter results write-up
```

`<topic>` is **user-chosen** (the problem class, e.g. a
graph-information-bottleneck comparison). It need not match any paper
slug.

> The conceptual `comparator`, when run standalone, writes its prose
> comparison under this same area (consistent with the parked roadmap
> intent of `comparisons/<topic>/comparison.md`). Exact filename for the
> standalone case to be settled in the build phase — candidate:
> `<vault_paperlab_path>/experiments/<topic>/comparison.md`.

### 4.2 Repo — code and data

```
sandbox/experiments/<topic>/
├── synth/         data-synthesis code
├── methods/       one implementation per compared method
├── run/           run scripts / entry points
├── data/          generated data — GIT-IGNORED, regenerable from seed
└── results/       run outputs (metrics, logs) consumed by evaluator
```

`sandbox/experiments/` is a dedicated namespace **to avoid collision
with the existing `sandbox/<slug>/` convention** (where `<slug>` is a
paper, and topic names like `GIB` would otherwise clash with the `GIB`
paper slug). Other files / older toy experiments continue to live
directly under `sandbox/`.

### 4.3 Data gitignore policy

Synthesized data can be large and is regenerable from a pinned seed, so
`sandbox/experiments/*/data/` is git-ignored. The *generator code* and
the *seed* are committed; the data itself is not.

## 5. Inputs

- `spec.md` for every paper in the comparison (always available).
- `code_map.md` / cloned upstream under `repo_upstream_dir(slug)` when
  present (improves implementation fidelity; not required).

## 6. Path helpers (added this session)

To honor the "no hard-coded paths" rule (`paperlab-config-bootstrap`),
two helpers were added to `tools/paths.py`:

- `repo_experiments_dir(topic)` → `<repo>/sandbox/experiments/<topic>/`
- `vault_experiments_dir(topic)` → `<vault>/experiments/<topic>/`

with matching `python -m tools.paths` CLI verbs (`exp-sandbox`,
`exp-vault`). No new config key was required — both derive from the
existing `repo_root` and `vault_paperlab_path`.

## 7. Skills (planned, not yet written)

| Agent | Skill |
|---|---|
| `experimenter` | `ml-experiment-design` |
| `comparator` | `ml-comparison` |
| `coder` | `ml-experiment-code` |
| `evaluator` | `ml-evaluation` |

## 8. Decision log

Every decision locked this session, with the *why*:

1. **Re-scope to multi-paper, problem-type-oriented, full lifecycle.**
   Single-paper toy framing was too narrow for the user's actual goal
   (compare 3+ methods on a problem class).
2. **Four agents, not one monolith.** Separation of concerns + reuse of
   the existing one-shot/in-session pattern.
3. **Model 3 (hybrid coding).** Heavy scaffold one-shot via `coder`;
   tight tweak loop in-session via `experimenter`. Best loop ergonomics
   without bloating the orchestrator; mirrors tutor/explainer.
4. **Split conceptual (`comparator`) from empirical (`evaluator`).**
   Different inputs, timing, outputs, judgment.
5. **`comparator` is dual-mode**; its input is durable (specs), so
   standalone use is well-defined and independently useful.
6. **`coder` and `evaluator` are backend-only.** `evaluator` routes
   through the experimenter.
7. **Notes in vault, code/data in repo.** Core PaperLab split.
8. **`sandbox/experiments/<topic>/` namespace** to avoid slug
   collision; `<topic>` is user-chosen.
9. **Data git-ignored, regenerable from seed.** Code + seed committed.
10. **`comparator` here is the same agent as the parked roadmap
    `comparator`** — un-parked and sharpened, not a new one.
11. **Coder verifier gate parked.** A future "does it run?" check
    (analogous to the dissector's LaTeX gate) is noted but not built
    now.
12. **`implementer` left as-is.** Authoring fresh sandbox code is the
    `coder`'s job; the implementer keeps its clean read-and-map-to-
    `code_map.md` contract.

## 9. Open questions (resolve in build phase)

1. Standalone `comparator` output filename (`comparison.md` under
   `experiments/<topic>/` vs. another location/scheme).
2. Build order. Proposed: **`comparator` first** — it is dual-mode,
   reads only durable artifacts, and is independently testable without
   the rest of the suite. Then `experimenter` (orchestrator shell) →
   `coder` → `evaluator`.
3. Whether `experiments/<topic>/` needs its own YAML front-matter
   `category`/`agent` conventions (the front-matter section in
   `AGENTS.md` currently enumerates per-paper agents only).
4. Coder verifier gate design (parked — §8.11).

## 10. Out of scope for this session

- Writing any agent prompt (`.cursor/agents/*.md`) or skill
  (`.cursor/skills/*/SKILL.md`).
- Building `tools` beyond the two path helpers.
- The coder verifier gate.
