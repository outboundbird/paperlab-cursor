# Stage 2 — Coder adapt-mode: kickoff & orientation

> **SUPERSEDED 2026-06-04** by
> [`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./2026-06-04-stage2-regime2-component-surgery-design.md).
> This file framed Stage 2 as black-box *wrapping* (Regime 1). The
> redesign establishes that PaperLab's valuable comparisons need
> *component-level surgery* (Regime 2) and reworks the Stage-2 design.
> Kept for historical context and the Regime-1 contrast.

**Status:** designed, not built. This file orients the Stage-2 work within
the project and gathers the settled decisions + open questions so a build
session can start without re-deriving context.

**Prereqs already shipped:** Stage 1 coder (`/coder code <slug>` →
`vault_code_dir(slug)/method.py` + `test_invariants.py`), validated
end-to-end on GENI; the experimenter design-phase shell (`design.md`).

**Source designs (read these first):**
- [`log/2026-06-03-two-stage-coder-design.md`](./2026-06-03-two-stage-coder-design.md) — the two-stage split; Stage-2 rationale.
- [`log/2026-05-29-experimenter-design.md`](./2026-05-29-experimenter-design.md) — the experimenter suite, seams, Model 3 (hybrid coding).
- `.cursor/skills/ml-experiment-code/SKILL.md` § "STAGE 2 — Coder adapt-mode (PLANNED)" — the placeholder contract Stage-1 output was shaped to fit.

---

## 1. What Stage 2 is

Stage 2 is the coder's **adapt-mode**: backend-only, invoked by the
`experimenter` during an experiment, never by the user directly. It does
**not** re-derive a method. It **wraps** the already-coded, paper-bound
Stage-1 `Method` to a shared experiment harness so several papers' methods
can run on the same synthetic data and be compared.

```
Stage 1 (shipped)   blueprint / official code
                      → runnable method.py + test_invariants.py
                        in vault_code_dir(slug) = <vault>/<slug>/code/

Stage 2 (this work) experimenter invokes coder adapt-mode
                      → thin adapter wrapping that Method to the topic harness
                        in repo_experiments_dir(topic)/methods/<slug>/
```

The payoff: at experiment time the two source branches **converge** —
"take paper-bound code, wrap to harness":

| | Paper-bound code | Stage 2 adaptation |
|---|---|---|
| Official code | `upstream/<slug>/` (clone) | wrap to harness |
| No code | `vault_code_dir(slug)` (Stage-1 output) | wrap to harness |

Stage 1's **hybrid `Method` contract** (paper-natural guts + one documented
entry point + declared I/O block) exists *specifically* so adapt-mode
starts from a stable handle instead of reverse-engineering a bespoke
signature each time.

## 2. Where it sits in the project

Stage 2 is one piece of the **experimenter suite** (multi-paper empirical
comparison on synthetic data). Suite status:

| Agent | Status | Role |
|---|---|---|
| `experimenter` | design-phase shell shipped | user-facing orchestrator; owns design + data-synthesis *decisions*; writes `design.md` / `findings.md` |
| `comparator` | shipped | conceptual cross-method comparison (`comparison.md`) |
| `coder` Stage 1 | shipped | per-paper runnable method code in the vault |
| **`coder` Stage 2** | **this work** | wrap Stage-1 code to the topic harness |
| `evaluator` | designed, not built | interpret empirical run outputs |

**Interaction model (Model 3, hybrid):** the `coder` does the heavy
scaffold one-shot; the `experimenter` does the tight write→check→tweak
loop in-session. Mirrors the `tutor`/`explainer` split. The `experimenter`
**only coordinates — it never writes method code**; all coding is the
coder's (generate in Stage 1, adapt in Stage 2). This is Seam A.

**Seam B (user-check gate):** between coder-writes and coder-runs, the user
reviews the written code before it executes.

This work **unblocks** the experimenter's implement→run→evaluate phases,
which today stop at the implement boundary.

## 3. Settled decisions (do not relitigate)

From the two-stage design log (resolved 2026-06-04) and the experimenter
design:

1. **Backend-only.** Adapt-mode is invoked by the `experimenter`, never by
   the user.
2. **Wrap, don't re-derive.** Input is the Stage-1 `Method` (stable handle)
   + the topic harness interface. Output is a thin adapter.
3. **Adapter location.** `repo_experiments_dir(topic)/methods/<slug>/`
   (in the repo's `sandbox/experiments/` tree — NOT the vault). Resolve via
   `tools/paths.py` (`repo_experiments_dir(topic)`); never hard-code.
4. **Stage 2 never edits the Stage-1 vault code.** The vault `method.py`
   stays the canonical, reusable implementation; the adapter is
   experiment-local glue.
5. **Guard.** The harness runs each adapter on the experiment's synthetic
   data; shape/interface mismatches surface there. Method-level correctness
   was already guarded by Stage-1 invariants — adapt-mode does not re-run or
   duplicate those.
6. **One skill, two sections.** Stage 2 fills out the existing PLANNED
   section in `.cursor/skills/ml-experiment-code/SKILL.md` (not a new skill).
7. **Hook scope unchanged.** The post-hoc verifier hook is `.md`-only and
   ignores `.py`; adapters are repo-side code and out of its scope anyway.

## 4. Open questions (resolve at build time)

The Stage-2 contract was deliberately left "to be finalized at build time."
Decide these before/while building:

- **Harness interface contract.** What exactly does the topic harness
  expect each method to expose? (A `predict(data) -> scores`? A
  `run(inputs) -> outputs` with a declared output schema per topic?) The
  experimenter defines the harness per topic — does adapt-mode read a
  harness spec file, or a Python ABC/protocol the harness ships?
- **Who authors the harness itself?** The per-topic harness (the common
  interface + the runner that feeds synthetic data and collects
  `results/`) is distinct from the per-method adapter. Is the harness
  written by the coder (one-shot scaffold, same invocation) or is it part
  of the experimenter's design output? (Experimenter design log § 3 implies
  the coder scaffolds data-synthesis + method code; confirm the harness
  shell is in that scaffold.)
- **Adapter file layout.** Single `adapter.py` under
  `methods/<slug>/`? Plus an `__init__`? How does the harness discover and
  import adapters (registry, naming convention, entry-point file)?
- **I/O reconciliation rules.** The Stage-1 `Method` I/O block uses
  paper-natural names/shapes; the harness uses topic-natural ones. What are
  the allowed transforms in the adapter (rename, reshape, batch, device
  placement) and what is forbidden (no re-implementing method logic)?
- **Non-learner methods.** A simulator (`run(params) -> trajectory`) and a
  closed-form method (`run(graph) -> scores`) must wrap as cleanly as a
  learner (`fit`/`predict`). Confirm the adapter contract does not assume a
  train step.
- **Failure surfacing.** When an adapter can't satisfy the harness
  (genuine I/O incompatibility, not a bug), how does adapt-mode report back
  to the experimenter — and does that become a row in `findings.md` /
  `design.md` rather than a silent skip?
- **Seam B mechanics.** Where exactly does the user-check gate fire for
  Stage-2 output — after the coder writes all adapters, before the harness
  runs? Reuse the experimenter's existing gate or add one in adapt-mode?

## 5. Build order (proposed)

1. (this file) capture the kickoff.
2. **Decide the harness contract** (§4 first three bullets) — everything
   else depends on it. Likely a short companion decision in the experimenter
   design, since the harness is shared across methods.
3. Fill out `.cursor/skills/ml-experiment-code/SKILL.md` § STAGE 2 with the
   finalized process, adapter file layout, I/O reconciliation rules, and
   self-checks (mirror the Stage-1 section's structure).
4. Build the coder's adapt-mode in `.cursor/agents/coder.md` (backend
   invocation path; reads Stage-1 `Method` + harness contract; writes
   adapter; reports back).
5. Wire the `experimenter` to invoke adapt-mode (Seam A) and route the
   user-check gate (Seam B).
6. Smoke test: take GENI's shipped `vault_code_dir("GENI")/method.py`,
   define a minimal topic harness, adapt it, run on synthetic data.
   (Note: `evaluator` is still unbuilt — the smoke test can stop at "harness
   runs the adapter and emits `results/`," with interpretation deferred.)
7. Update `AGENTS.md`, `ROADMAP.md`, `README.md` (remove the Stage-2
   PLANNED notices; mark the coder fully shipped).

## 6. Dependencies / sequencing note

Stage 2 is wrappable independently, but a **full** experiment run also
needs the `evaluator` (empirical results interpretation) to produce
`findings.md`. Two viable orders:

- **Stage 2 first** (this file's order): land adapt-mode + harness, smoke
  test to "results emitted," then build `evaluator`.
- **Pair them:** build Stage 2 and `evaluator` together so the first real
  experiment is end-to-end.

Pick at build time based on whether you want a runnable harness milestone
before the evaluator exists.
