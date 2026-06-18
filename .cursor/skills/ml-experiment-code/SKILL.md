---
name: ml-experiment-code
description: Defines how the Coder subagent turns a paper's method into runnable code. Stage 1 (standalone, per-paper) writes invariant-validated method code to `vault_code_dir(slug)` from the paper's `code_blueprint.md` or official upstream code. Stage 2 has two regimes, both invoked by the experimenter and written under `repo_experiments_dir(topic)`: **component surgery** (multi-method) synthesizes a shared scaffold and extracts each paper's divergent component into `methods/<slug>/extracted.py`; **extension regime** (single-method) inherits/composes the audited Stage-1 `method.py` into `methods/<slug>/extended.py` for ablations, sensitivity sweeps, or planted-signal studies of one paper. Use when implementing, coding, extending, or adapting a paper's method.
---

# ML Experiment Code Schema

## Purpose

This skill defines what the **Coder** subagent produces. The Coder is the
only PaperLab agent that writes **runnable code**. It works in two stages,
covered by the two clearly-marked sections below. Read the section for the
stage you are in and treat it as authoritative; do not blend the two.

```
blueprint (or official code)
        |  STAGE 1 — standalone per-paper coder (this section, below)
   runnable, invariant-validated method code in the VAULT: vault_code_dir(slug)
        |  STAGE 2 — coder component surgery (invoked by the experimenter)
   shared scaffold + extracted divergent components in the REPO:
   repo_experiments_dir(topic)/  (scaffold.py + methods/<slug>/extracted.py)
```

Stage 2 is **not** black-box wrapping. The valuable PaperLab comparisons
hold a shared *principle* fixed (e.g. the information bottleneck) and swap
the *divergent component* inside it (e.g. the bottleneck sampling step).
That requires reaching inside each method, not wrapping it. Full design:
[`log/2026-06-04-stage2-regime2-component-surgery-design.md`](../../../log/2026-06-04-stage2-regime2-component-surgery-design.md).

Stage 1 is the hop-2 guard of the two-hop fidelity model: paper math →
`code_blueprint.md` (hop 1, guarded by the Critic pre-emission) →
**runnable code (hop 2, guarded here)**. The blueprint's §4 invariants
become runtime assertions the Coder runs on synthetic input before
declaring the code done.

## Two source branches, one Stage-1 job

A paper reaches Stage 1 by one of two routes, and Stage 1 normalizes
them into the same artifact — reusable, paper-bound method code in the
vault:

| Route | Source read | Stage-1 input |
|---|---|---|
| No official code | `vault_path(slug, "code_blueprint.md")` | the blueprint contract |
| Official code exists | `repo_upstream_dir(slug)` + `vault_path(slug, "code_map.md")` | the mapped implementation |

The blueprint route is the primary one (it is *why* the Coder exists —
to make no-code papers runnable). The official-code route is a
re-expression: a clean, self-contained reimplementation distilled from
the upstream clone, useful when the upstream code is too entangled to
plug into an experiment directly. **Default to the blueprint route**;
only take the official-code route when the user explicitly asks to
reimplement existing code.

---

# STAGE 1 — Standalone per-paper coder

Stage 1 is **user-invokable** and produces, for one paper, runnable
method code plus its invariant checks, written to `vault_code_dir(slug)`
(i.e. `<vault>/<slug>/code/`, resolved via `tools/paths.py`). No harness,
no experiment — Stage 1 stands alone and is the standalone hop-2 smoke
test.

## Stage-1 conventions

- **Audience:** a reader fluent in ML and Python who will review this
  code by hand. Faithfulness to the blueprint and readability matter
  more than cleverness.
- **Framework:** PyTorch by default (PaperLab convention), unless the
  blueprint or user names another. State the chosen framework in the
  module docstring. Keep dependencies minimal — prefer the standard
  library + the chosen framework + NumPy; do not pull in heavy extras
  for convenience.
- **Faithfulness:** implement the blueprint's §3 steps in order, using
  **paper-natural names** for internal variables (mirror the blueprint /
  spec notation). The point is that a reader can diff the code against
  the blueprint step by step.
- **Type hints + NumPy-style docstrings** (PaperLab Python convention).
- **No training runs, no real data, no downloads.** Stage 1 validates
  on **synthetic** input only (small random tensors with the blueprint's
  declared shapes). It must run in seconds on CPU.
- **Determinism:** seed any RNG used in the invariant checks so the
  asserts are reproducible.

## Stage-1 file layout (`vault_code_dir(slug)`)

Resolve the directory with `python -m tools.paths code-dir <slug>` and
create it if missing. Multiple files are allowed:

- **`method.py`** (required) — the implementation: the paper-natural guts
  plus the hybrid `Method` wrapper (see below).
- **`test_invariants.py`** (required) — the blueprint §4 invariants as
  executable assertions on synthetic input. Runnable directly
  (`python test_invariants.py`) and exits non-zero on any failure.
- **`README.md`** (optional, bare stub) — a few lines only: what the
  method is, that it is reconstructed-from-blueprint (not official), and
  how to run the invariant check. It does **not** contain a code
  walkthrough. The algorithm↔code walkthrough is the **implementer's**
  job: after Stage 1, the implementer maps `method.py` into `code_map.md`
  (the same artifact official-code papers get), and the critic audits it
  against the spec. See "Where the walkthrough lives" below.

If `method.py` already exists, apply the regenerate-prompt rule
(`.cursor/rules/paperlab-regenerate-prompt.mdc`): ask replace / append /
abort before overwriting. (Append rarely makes sense for code; replace
or abort are the usual answers — but still ask.)

## The hybrid `Method` interface contract

The implementation is **paper-natural inside**, **predictable at the
boundary**. Every Stage-1 `method.py` exposes one class — the `Method`
wrapper — that gives Stage-2 adapt-mode a stable handle without having to
reverse-engineer a bespoke signature. The wrapper requires exactly three
things:

1. **A constructor** taking the method's declared hyperparameters as
   keyword arguments with defaults from the blueprint §2 / spec §7. No
   hidden global state.
2. **One documented entry point.** Name it `run` for the general case, or
   `forward` if the class is an `nn.Module` and `forward` is the natural
   entry. It takes the declared inputs and returns the declared output.
3. **An I/O contract block** in the class docstring, lifted from the
   blueprint §2: each input's name + shape + dtype, and the output's
   name + shape + dtype.

```python
class Method:
    """<paper-natural method name> — <one line>.

    I/O contract (from code_blueprint.md §2)
    ----------------------------------------
    Inputs:
        graph : adjacency, shape [N, N], float
        ...
    Output:
        scores : node importance, shape [N], float
    """

    def __init__(self, *, alpha: float = 0.85, n_iter: int = 100) -> None:
        ...

    def run(self, graph):  # or forward(self, ...) for an nn.Module
        ...
```

**`fit` / `predict` are OPTIONAL.** Add them only when the method is a
learner and they are natural (GENI, a supervised ranker, is one such
case). Non-learners stay compliant with constructor + entry point + I/O
block alone:

- a **simulator** exposes `run(params) -> trajectory`;
- a **closed-form** method (e.g. a centrality score) exposes
  `run(graph) -> scores`.

Never force a supervised-learner mold onto a method that is not one.

## Where the walkthrough lives (NOT the coder's job)

The coder does **not** write the algorithm↔code walkthrough. That is the
**implementer's** `code_map.md`, produced *after* Stage 1: the implementer
maps the coder's `method.py` against `spec.md` exactly as it maps official
upstream code (see `ml-code-map` "Two sources, one schema", `reconstructed`
source), and the critic then audits that `code_map.md` against the spec
(the firewalled hop-2-vs-spec check). This keeps one walkthrough format
and one author (implementer) whether or not a paper shipped code, and
keeps the *author of the code* (coder) from also documenting/auditing it.

So the coder's job ends at `method.py` + `test_invariants.py` (+ an
optional bare-stub `README.md`). The reader who wants the
component-by-component walkthrough reads `code_map.md`; the reader who
wants to know what "invariants passed" means reads the critic's
reconstructed-source §4. The post-Stage-1 chain:

```
coder: method.py + test_invariants.py
   → implementer: map method.py vs spec → code_map.md  (the walkthrough)
   → critic: audit code_map vs spec → critic_reviews.md (the firewall)
```

## Stage-1 process

0. Read this section. Resolve the route (blueprint vs official code) and
   the prerequisites below.
1. **Prerequisites.**
   - `vault_path(slug, "spec.md")` must exist (shared context). If
     absent, tell the user to run the dissector first and end the turn.
   - Blueprint route: `vault_path(slug, "code_blueprint.md")` must exist.
     If absent, tell the user to run `/implementer blueprint <slug>`
     first and end the turn.
   - Official-code route (only when the user asked to reimplement):
     `repo_upstream_dir(slug)` must exist; read `code_map.md` if present.
2. **Read the source** (blueprint §2/§3/§4, or the upstream code +
   code_map). Build the implementation plan in working memory: the
   ordered steps, the symbol/shape table, and the invariant list.
3. **Write `method.py`** — implement §3 steps in order with paper-natural
   names, wrapped by the `Method` class. Bind every blueprint symbol to a
   code variable so a reader can diff the two.
4. **Write `test_invariants.py`** — translate **every** blueprint §4
   invariant into an assertion on small synthetic input (shapes from §2).
   Cover at minimum the shape invariants for every named output, plus
   every normalization / sign / range / conservation property §4 lists.
   Use a numerical tolerance for value checks. Seed the RNG.
5. **Run `test_invariants.py`** (this is the hop-2 guard). It must pass.
   - **Timeout.** Cap each invocation at the Stage-1 timeout from
     `tools.paths.coder_smoke_timeouts()` (default 30s; user-configurable
     in `paperlab.config.yaml` under `coder_smoke_timeout.stage1` for
     slower hardware). A run that exceeds the budget counts as a FAIL,
     not a skip — bump the config and re-run rather than disabling the
     check.
   - On failure: fix `method.py` (the code is wrong, not the invariant —
     the invariant came from the critic-approved blueprint). Re-run.
   - **Budget: 3 fix attempts.** If still failing, do not claim success:
     report which invariant fails, the observed vs. expected, and end the
     turn. Leave the failing code and test in place so the user can
     inspect.
6. **Optionally write a bare-stub `README.md`** — a few lines: method
   name, the reconstructed-not-official disclaimer, and the run command.
   No walkthrough (that is the implementer's `code_map.md`).
7. Run the Stage-1 self-checks and report back. Suggest the next step:
   `/implementer map <slug>` (to produce the `code_map.md` walkthrough),
   then `/critic audit <slug>`.

## Stage-1 self-checks

- `method.py` exposes exactly one `Method` class with a constructor, one
  documented entry point, and the I/O contract block in its docstring.
- Every blueprint §3 step maps to identifiable code (paper-natural
  names); no step silently dropped.
- `test_invariants.py` has an assertion for **every** §4 invariant, runs
  on synthetic input in seconds on CPU, and **passes**.
- No code walkthrough was written by the coder (that is the implementer's
  `code_map.md`). Any `README.md` is a bare stub only.
- No real data, no downloads, no training run, no network.
- `fit`/`predict` present only if the method is genuinely a learner.
- Framework named in the module docstring; dependencies minimal.

## Stage-1 reporting back

- The paths written under `vault_code_dir(slug)` (`method.py`,
  `test_invariants.py`, and an optional bare-stub `README.md`).
- The route taken (blueprint or official-code reimplementation).
- The invariant-check outcome: PASS (N invariants checked), or the
  failing invariant(s) with observed-vs-expected if the fix budget was
  exhausted (code left in place, not claimed correct).
- The suggested next step: `/implementer map <slug>` → `/critic audit
  <slug>` for the walkthrough + firewalled code↔spec check.
- Any `⚠️ UNCERTAIN:` flags for blueprint quantities that forced a
  judgment call in code.
- A reminder that on the blueprint route this is reconstructed code, not
  the authors' implementation.

## Stage-1 scope boundaries

- Writes only under `vault_code_dir(slug)`. Does **not** write to
  `papers/`, `sandbox/`, or the rest of the per-paper vault folder.
- Does not modify `spec.md`, `code_blueprint.md`, `code_map.md`, or any
  upstream code (read-only).
- Does not run real experiments, train on real data, or download
  datasets — synthetic-input invariant checks only.
- Does not build a harness or adapt to one — that is Stage 2.

---

# STAGE 2 — Coder component surgery (invoked by the experimenter)

Stage 2 is **backend-only**, invoked by the `experimenter` during an
experiment, never by the user directly. It is **component surgery**, not
black-box wrapping: it synthesizes a shared scaffold that holds the
experiment's principle + task fixed, and extracts each member paper's
**divergent component** into that scaffold's pluggable slot so the
variants can be compared on equal footing.

The kickoff framing of Stage 2 as "wrap the Stage-1 `Method` to a harness"
([`log/2026-06-04-stage2-coder-adapt-kickoff.md`](../../../log/2026-06-04-stage2-coder-adapt-kickoff.md))
is **superseded** by the component-surgery design
([`log/2026-06-04-stage2-regime2-component-surgery-design.md`](../../../log/2026-06-04-stage2-regime2-component-surgery-design.md)).

## What Stage 2 compares (the two regimes)

| | Regime 1 (NOT this) | Regime 2 (this) |
|---|---|---|
| Compared | whole methods on a shared task | one divergent component inside a shared principle |
| Built | thin adapter | shared scaffold + extracted components |
| Touches internals? | no | yes — by design |

Stage 2 implements **Regime 2**. If a comparison genuinely is Regime 1
(methods interchangeable on a shared task, no internal divergence to
isolate), the scaffold collapses to a trivial slot that calls each
`Method`'s entry point — but the agent still follows the Regime-2 process
below; it does not special-case a wrapper.

## Settled principles (do not relitigate)

1. **Borrow, not reinvent.** Reuse the paper's method logic; never
   re-implement it. The divergent component is lifted from the paper's
   code, not rewritten.
2. **Per-paper code is immutable.** Stage 2 never edits `<slug>/code/`
   (Stage-1 `method.py`) or upstream code. Refactors land under the topic,
   never written back to the paper folder.
3. **No member paper is the host.** The scaffold is synthesized fresh; it
   does not adopt one paper's training loop and bolt others into it.
4. **The seam is a design decision.** Where the scaffold is cut (what is
   held fixed vs. swapped) is co-designed by the experimenter + user and
   recorded in `design.md`. The coder builds against that seam; it does
   not choose it.
5. **Nothing agent-invented goes unchecked.** Extracted components and the
   synthesized scaffold are both fidelity-gated by the critic before the
   experiment runs (see "Fidelity gates").

## Inputs

- The **seam contract** from `design.md` (prose): what the scaffold holds
  fixed (principle + task), where the pluggable slot is, and what each
  member paper's divergent component is.
- Each member paper's **`code_map.md`** (the concept→code map — the
  primary anchor for *where* the divergent component lives in the source)
  and **`spec.md`** (the described mechanism).
- Each member paper's source code: Stage-1 `vault_code_dir(slug)/method.py`
  (reconstructed) or `repo_upstream_dir(slug)` (official). Resolve vault
  paths with `python -m tools.paths code-dir <slug>` **before** reading —
  the vault is outside the workspace and relative search will not find it.

## File layout (`repo_experiments_dir(topic)`)

Resolve the directory with `python -m tools.paths exp-sandbox <topic>`.

```
sandbox/experiments/<topic>/
├── scaffold.py            agent-synthesized; principle + task fixed; defines the slot Protocol
├── methods/
│   └── <slug>/
│       ├── __init__.py
│       └── extracted.py   the paper's divergent component, fitted to the slot (provenance header)
├── run.py                 driver: synth data → each variant through the scaffold → results/
└── results/              run outputs (git-ignored under data/ if bulky)
```

`scaffold.py` and `run.py` are the per-topic shared shell; `methods/<slug>/`
is one folder per member paper.

## The scaffold contract

`scaffold.py` formalizes the seam from `design.md` as a Python
`Protocol` (or ABC) — the slot every extracted component plugs into — and
holds the fixed pipeline around it. The slot signature is the **union** of
all members' needs (if one variant needs `data.x` and another only `h`,
the slot carries both). Sketch (the exact shape comes from the topic's
seam):

```python
from typing import Protocol
from torch import Tensor

class BottleneckComponent(Protocol):
    """The pluggable slot (from design.md seam). Each member paper's
    divergent mechanism conforms to this."""
    def __call__(self, h: Tensor, x: Tensor, edge_index: Tensor) -> tuple[Tensor, Tensor]:
        """returns (z, reg): bottlenecked repr + IB regularizer term."""
        ...

def run_experiment(data, component: BottleneckComponent):
    h = encoder(data.x, data.edge_index)        # fixed (principle/task)
    z, reg = component(h, data.x, data.edge_index)  # the SLOT (varies per paper)
    y_hat = readout(z)                           # fixed
    loss = task_loss(y_hat, data.y) + beta * reg # fixed objective form
    return y_hat, loss
```

What is fixed (encoder, readout, objective form) encodes the **shared
principle** the papers claim — so the scaffold itself is a fidelity
concern (see gates).

## The borrow ladder (per member paper)

For each paper, produce `methods/<slug>/extracted.py` by the cheapest
faithful route:

1. **Import directly** — if the divergent component is already cleanly
   separable in the source (a standalone function/class), import it and
   adapt only I/O names/shapes to the slot. `extracted.py` is then a thin
   conformer around the imported symbol.
2. **Extract-and-refactor** — if the component is entangled (e.g. the
   bottleneck sampling is fused into a monolithic `forward()`), refactor
   the original logic out into `extracted.py`, **preserving the original
   computation** (same order, same ops, same constants). This is the
   common case for the comparisons PaperLab cares about.

**Allowed in `extracted.py`:** rename, reshape, re-order I/O to fit the
slot; relocate the divergent logic out of its original surroundings;
device/dtype placement. **Forbidden:** changing what the component
computes — no new terms, no dropped terms, no swapped distributions, no
"improvements." If you cannot fit the slot without altering the
computation, that is a failure to surface (see below), not a license to
edit the method.

## Provenance header (every `extracted.py`)

```python
"""<slug> — <component name> extracted for experiment <topic>.

Source: <slug>/code/method.py  (or repo_upstream_dir(<slug>)/<file>)
Source location: code_map.md §<n> / <function-or-class>, lines <a>–<b>
Status: EXTRACTED + REFACTORED — not the original module layout.
        Computation preserved; only I/O reshaped to the scaffold slot.
Borrow route: import-direct | extract-and-refactor
"""
```

## Fidelity gates (before the experiment runs)

Two judgment gates (critic) plus one opportunistic empirical check
(coder). The critic is invoked by the **experimenter** (it owns the
verdict); the coder runs the behavioral check when feasible and feeds the
result in as evidence.

1. **Extraction-fidelity (critic, hard gate, per paper).** The critic
   audits each `extracted.py` against `code_map.md` (primary) + `spec.md`
   (secondary): does the extracted component still compute the paper's
   mechanism? It also audits the **wiring in `run.py`** around the
   component — any backbone you reimplement instead of extract (e.g. a
   hand-rolled GAT vs. the paper's `GATConv`) must be declared and
   behavior-preserving, and **every** term of the method's mechanism (all
   IB / regularization / MI terms) must be wired or explicitly scoped out
   in `design.md`. A dropped term or an undeclared backbone swap fails the
   gate even if `extracted.py` itself is clean. FAIL blocks that variant.
   Retry budget max 2 (fix the extraction or wiring, re-audit); on
   exhaustion, escalate to the user and surface in `findings.md` — do not
   silently drop.
2. **Scaffold-fidelity (critic).** The critic audits `scaffold.py`'s fixed
   part against the shared principle the papers claim (e.g. is the IB
   objective form faithful?). A wrong scaffold measures every variant
   under a wrong objective.
3. **Behavioral equivalence (coder, opportunistic).** When a component is
   runnable in isolation, run the *original* and the *extracted* version
   on the same seeded synthetic input and assert outputs match within
   tolerance. Often infeasible (if it ran cleanly in isolation it could
   usually have been imported) — skip when not applicable; it corroborates
   the critic gate, it is not a substitute for it.

## Stage-2 process

0. Read this section. Read the seam contract from `design.md` and the
   member-paper list.
1. **Resolve paths.** `exp-sandbox <topic>` for the output tree; for each
   paper, `code-dir <slug>` (reconstructed) or `repo_upstream_dir(slug)`
   (official) for the source, and resolve `code_map.md` / `spec.md`.
2. **Synthesize `scaffold.py`.** Build the fixed pipeline from the seam;
   declare the slot `Protocol` as the union of member needs. Paper-natural
   names for the principle's quantities so the critic can diff it.
3. **For each member paper, write `methods/<slug>/extracted.py`** via the
   borrow ladder. Stamp the provenance header. Conform to the slot without
   altering the computation.
4. **Write `run.py`** — generate the experiment's synthetic data (per
   `design.md` §4), run each variant through `scaffold.run_experiment`,
   collect into `results/`. Seed everything.
5. **Behavioral-equivalence checks** (coder) where feasible; record
   PASS/skip per paper to hand to the critic gate.
6. **Smoke gate.** After the experimenter's critic gates (extraction-
   fidelity Check A + scaffold-fidelity Check B) have passed, run
   `python run.py --smoke` as the end-to-end execution check (see
   "Stage-2 smoke gate" below). PASS / FAIL / TIMEOUT is reported
   verbatim to the experimenter; FAIL or TIMEOUT blocks the build,
   1 retry allowed.
7. **Report back to the experimenter** with the artifacts, the
   borrow route per paper, the behavioral-check results, the smoke-gate
   outcome, and any extraction that could not be fitted faithfully. The
   experimenter runs the critic gates and routes the user-check
   (Seam B) before any run is trusted.

Stage 2 does **not** itself decide the design, write `design.md`, or
interpret results — those are the experimenter's and evaluator's.

## Stage-2 smoke gate (`run.py --smoke`)

The fidelity gates (critic) cover the static question "does the code
faithfully implement what the paper says". They cannot tell you that
`run.py` actually executes end-to-end on the synthetic inputs `design.md`
describes. The smoke gate is that runtime check, ordered **after** the
critic's gates pass and **before** the coder reports back — so a smoke
run is never wasted on code the critic will reject.

### What `--smoke` must mean

`run.py` must accept a `--smoke` flag whose code path is the smallest
end-to-end execution that still touches every variant the experiment
will run. Specifically:

- **One condition per variant** (component-surgery: one slug per
  `methods/<slug>/extracted.py`; extension regime: the single extended
  variant plus the base condition if `design.md` calls for one).
- **One seed**, **one batch**, **one epoch** (or whatever the smallest
  semantically valid unit is for this design).
- **No checkpointing, no plotting, no large-file I/O.** The smoke run
  must not write to `results/` proper. If intermediate scratch output
  is unavoidable, write to `results/.smoke/` and remove that folder
  before `run.py` exits.
- **Exits non-zero on any unhandled exception**, including a CUDA OOM
  or a shape mismatch from the slot Protocol.
- **Deterministic** — the seed is the same one `design.md` §4 names.

### Timeout (per-machine)

Cap the run at the Stage-2 timeout from
`tools.paths.coder_smoke_timeouts()` (default 60s; user-configurable in
`paperlab.config.yaml` under `coder_smoke_timeout.stage2` for slower
hardware). On exceeding the budget, kill the process and report
TIMEOUT. The user fixes by either bumping the config (slow hardware)
or fixing the hang (real bug).

### Verdict + retry

| Outcome | Reported as | Action |
|---|---|---|
| Exit 0 within budget | `Smoke gate: PASS (Ns)` | Proceed to report-back. |
| Exit non-zero | `Smoke gate: FAIL (...)` | 1 retry: fix and re-run. Second FAIL → report and end the turn; do not claim success. Leave the failing code in place. |
| Hit timeout | `Smoke gate: TIMEOUT (Ns)` | 1 retry (with caveat: a real hang will TIMEOUT again). Second TIMEOUT → report and end the turn; suggest bumping `coder_smoke_timeout.stage2` if hardware-bound, or inspecting for an infinite loop. |

On FAIL or TIMEOUT, include a stderr excerpt (last ~20 lines) in the
report so the user can read the failure without re-running.

### When the gate is skipped

The default is to run the smoke gate for both regimes. It is skipped
only when `design.md` explicitly says so (a rare case where the
opportunistic behavioral-equivalence check covers the same ground —
typical for some single-attribute extension experiments). Record the
skip with `Smoke gate: SKIPPED — <reason from design.md §N>` in the
report-back.

## Failure surfacing (no silent drops)

- A component that cannot be faithfully extracted/fitted, or two papers
  that cannot share a faithful seam, is reported to the experimenter for
  recording in `design.md` (design-time infeasibility) or `findings.md`
  (run/audit-time failure). A blocked variant is named, not dropped.

## Stage-2 self-checks

- `scaffold.py` exposes the slot as a `Protocol`/ABC matching the
  `design.md` seam; the fixed part encodes the shared principle with
  paper-natural names.
- Every member `methods/<slug>/extracted.py` conforms to the slot, carries
  a provenance header, and (by inspection) preserves the source
  computation — no added/dropped/swapped logic.
- The borrow route (import-direct vs. extract-and-refactor) is recorded
  per paper.
- No `<slug>/code/` or upstream file was modified (read-only on sources).
- `run.py` seeds RNG and writes to `results/`; no real datasets/downloads
  unless `design.md` explicitly calls for small real data.
- Behavioral-equivalence outcome recorded per paper (PASS / skipped +
  why).
- Any unfittable extraction is surfaced for `design.md`/`findings.md`, not
  silently omitted.
- `run.py` accepts `--smoke` (one condition per variant, one seed, one
  batch, no checkpointing/plotting, deterministic, exits non-zero on
  any error). The smoke gate ran after the critic's gates and reported
  PASS / FAIL / TIMEOUT to the experimenter (or SKIPPED with a
  `design.md` reason).

## Stage-2 scope boundaries

- Writes only under `repo_experiments_dir(topic)`. Does **not** write to
  the vault, `papers/`, or any per-paper `<slug>/` folder.
- Does not edit Stage-1 vault code or upstream code (read-only).
- Does not choose the seam, write `design.md`, or interpret results.
- Does not alter what an extracted component computes to make it fit.
- Does not own the fidelity verdict — the critic does; the coder only
  builds and runs the behavioral check.

---

# STAGE 2 — Extension regime (single-method, invoked by the experimenter)

The component-surgery sections above assume **two or more** member
papers — the comparison's whole point is to swap a divergent component
across them. A growing class of PaperLab experiments studies **one**
paper's method on its own (component contributions, sensitivity sweeps,
robustness checks, planted-signal recovery against the paper's own
mechanism). For these, there is no shared principle to render and no
divergent component to slot, so building a `scaffold.py` is dead weight
and the extraction-fidelity gate has nothing to compare across.

Extension regime handles this case. It is still **Stage 2**
(experimenter-invoked, written under `repo_experiments_dir(topic)`,
fidelity-gated by the critic before run) — only the artifact set and the
gate change.

## When to use extension regime

Use extension when **all** are true:

- The experiment touches exactly one paper.
- `design.md` records a research type that is single-method by
  construction (ablation, sensitivity, reproduction, exploration of one
  method's behavior, or `custom` where the user makes the same scope
  call).
- The Stage-1 `method.py` exists for that paper (so there is something
  audited to extend).

If the experiment grows a second method later, the experimenter promotes
it to component surgery — extension is not a forever home.

## File layout (`repo_experiments_dir(topic)`)

```
sandbox/experiments/<topic>/
├── methods/
│   └── <slug>/
│       ├── __init__.py
│       └── extended.py    inherits/composes Stage-1 method.py; adds the experiment's modification
├── synth/
│   └── generate.py        synthetic data + planted signal per design.md §4
├── run.py                 driver: synth → conditions on extended → results/
└── results/              run outputs
```

No `scaffold.py`, no shared principle, no slot `Protocol`. The base
method is the audited Stage-1 `method.py` (or, for an `official`-source
paper, the upstream code referenced through `code_map.md`); `extended.py`
is its experiment-specific extension.

## What `extended.py` may and may not do

The base method is **immutable** — `extended.py` must not silently
re-implement it. Allowed shapes, in preference order:

1. **Subclass.** `class ExtendedMethod(Method): ...` overriding only the
   pieces the experiment varies (the bottleneck step, a regularizer
   weight, an attention head count). The base computation runs through
   the parent class, which is the audited code.
2. **Compose.** Hold a `Method` instance as an attribute and wrap its
   entry point. Use this when the experiment needs to interpose around
   the call (e.g. perturb inputs before forward, post-process outputs)
   rather than swap an internal step.

**Forbidden:** copying `method.py` into `extended.py` and editing it,
hand-rolling a "simpler" version of the base method "for the experiment",
or otherwise routing around the audited code. If the experiment cannot
be expressed by override / composition, surface that to the experimenter
— do not duplicate the method.

Every override or composition wrapper carries a provenance comment
naming the `code_map.md §` (or `method.py` symbol) it extends and what
the experiment varies.

## Provenance header (every `extended.py`)

```python
"""<slug> — extended for experiment <topic>.

Base method: <slug>/code/method.py  (or repo_upstream_dir(<slug>)/<file>)
Base reference: code_map.md §<n> / <symbol>
Extension scope (per design.md §<n>): <one-line description of what is varied / added>
Status: EXTENDED — base computation runs through the audited base method.
        Overrides are limited to the scope above.
"""
```

## Fidelity gate (extension-fidelity, critic)

Replaces the multi-method extraction-fidelity gate. The critic audits
`extended.py` and `run.py` against the paper's mechanism per
`.cursor/skills/ml-critique/SKILL.md` § "Extension-fidelity mode":

- **Check A — extension fidelity.** Each override is either authorized
  by `design.md` or consistent with the spec; nothing silently rewrites
  the base method.
- **Check A1 — context faithfulness.** `run.py` instantiates the
  extended class (which composes / inherits the audited base) — not a
  hand-rolled stand-in — and wires every in-scope mechanism term per
  `spec.md` / `code_map.md`.

There is no Check B (no scaffold). Behavioral-equivalence checks remain
opportunistic — when the experiment varies a single attribute, it is
often natural to assert that with that attribute set to the base value
the extended method matches the base method's outputs on seeded input.

Retry budget and escalation are the same as extraction-fidelity (max 2,
escalate on exhaustion, record in `findings.md`).

## Extension-regime process

0. Read this section. Read the experiment's `design.md` (research type,
   the single member slug, the extension scope, `synth` plan §4).
1. **Resolve paths.** `exp-sandbox <topic>` for the output tree;
   `code-dir <slug>` (reconstructed) or `repo_upstream_dir(slug)`
   (official) for the base method; `code_map.md` / `spec.md` for the
   anchors.
2. **Write `methods/<slug>/extended.py`** as a subclass or composition
   of the base `Method`. Override only what `design.md` authorizes.
   Stamp the provenance header.
3. **Write `synth/generate.py`** per `design.md` §4 — synthetic data and
   planted signal. Seed deterministically.
4. **Write `run.py`** — instantiate `ExtendedMethod` (or the wrapper),
   run each condition on synthetic data, write to `results/`. No real
   datasets unless `design.md` explicitly calls for small real data.
5. **Behavioral-equivalence check** (opportunistic) where the design
   permits a "neutral" setting that should reproduce the base method.
   Record PASS / skipped+why.
6. **Smoke gate.** After the experimenter's extension-fidelity gate
   passes, run `python run.py --smoke` per "Stage-2 smoke gate" above
   (same semantics: one condition, one seed, one batch, no
   checkpointing/plotting; same per-machine timeout
   `coder_smoke_timeout.stage2`; same 1-retry policy on FAIL or
   TIMEOUT).
7. **Report back to the experimenter** — artifacts, the override / compose
   choice, behavioral-check outcome, smoke-gate outcome, and any
   extension that could not be expressed without duplicating the base.
   The experimenter runs the extension-fidelity gate before any run
   is trusted.

## Extension-regime self-checks

- `extended.py` subclasses or composes the base `Method`; it does not
  copy or hand-reimplement it.
- Every override is named in the provenance header and authorized by
  `design.md` (or is a tightening consistent with `spec.md`).
- `run.py` instantiates `ExtendedMethod` (no silent base-method
  stand-in) and wires every in-scope mechanism term per `spec.md` /
  `code_map.md`.
- No `<slug>/code/` or upstream file was modified.
- Behavioral-equivalence outcome recorded (PASS / skipped + why).
- Any unexpressible extension is surfaced for `design.md`/`findings.md`,
  not silently rewritten.
- `run.py --smoke` was run after the extension-fidelity gate passed
  and reported PASS / FAIL / TIMEOUT to the experimenter (or SKIPPED
  with a `design.md` reason). On FAIL/TIMEOUT after one retry, the
  failing code is left in place and success is not claimed.

## Extension-regime scope boundaries

Same as Stage-2 component-surgery scope boundaries (vault is read-only,
fidelity verdict is the critic's, etc.) plus:

- Does **not** synthesize a `scaffold.py` or define a slot `Protocol`.
- Does **not** introduce a second member paper. If a comparison is
  needed, surface that to the experimenter for promotion to component
  surgery — extension does not silently grow a peer method.
