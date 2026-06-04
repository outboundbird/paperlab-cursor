---
name: ml-experiment-code
description: Defines how the Coder subagent turns a paper's method into runnable code. Stage 1 (standalone, per-paper) writes invariant-validated method code to `vault_code_dir(slug)` from the paper's `code_blueprint.md` or official upstream code. Stage 2 (adapt-mode, invoked by the experimenter) wraps that code to a topic harness under `repo_experiments_dir(topic)`. Use when implementing, coding, or adapting a paper's method for reuse or experiments.
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
        |  STAGE 2 — coder adapt-mode (invoked by the experimenter)
   wrapped to the topic harness: repo_experiments_dir(topic)/methods/<slug>/
```

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

# STAGE 2 — Coder adapt-mode (PLANNED — not yet built)

> **Status: designed, not implemented.** This section is a placeholder
> describing the intended Stage-2 contract so the Stage-1 output is
> shaped to fit it. Do not act on this section until Stage 2 is built and
> this notice is removed.

Stage 2 is **backend-only**, invoked by the `experimenter` during an
experiment, never by the user directly. It does not re-derive the method:
it **wraps** the Stage-1 `Method` from `vault_code_dir(slug)` to the
experiment's common harness interface and writes the thin adapter to
`repo_experiments_dir(topic)/methods/<slug>/`.

Intended contract (to be finalized at Stage-2 build time):

- **Input:** the Stage-1 `Method` (stable handle: constructor + entry
  point + I/O block) and the topic harness interface the experimenter
  defines.
- **Output:** an adapter under
  `repo_experiments_dir(topic)/methods/<slug>/` mapping the harness's
  expected calls onto the `Method`'s entry point, reconciling I/O names
  and shapes per the harness contract.
- **Guard:** the harness runs each adapter on the experiment's synthetic
  data; shape/interface mismatches surface there. (The method-level
  correctness was already guarded by Stage-1 invariants.)
- Stage 2 does not edit the Stage-1 vault code — the vault method stays
  the canonical, reusable implementation; the adapter is experiment-local
  glue.

When Stage 2 is built, this section will gain a full process, file
layout, and self-checks mirroring the Stage-1 section above.
