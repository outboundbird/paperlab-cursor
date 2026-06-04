# 2026-06-04 — Stage 2 coder redesign: component surgery (Regime 2)

Design-only session (Ask mode). No code written. **Supersedes the
Regime-1 assumptions in
[`log/2026-06-04-stage2-coder-adapt-kickoff.md`](./2026-06-04-stage2-coder-adapt-kickoff.md)**
— that kickoff designed Stage 2 as black-box *wrapping*; this session
establishes that the comparisons PaperLab actually cares about need
*component-level surgery*, and reworks the Stage-2 design accordingly.
Build deferred to a later session.

## Trigger

Working through the kickoff log's open questions (§4, "harness
interface contract"), the user observed that the kickoff's adapter model
assumes **method-level swapping** — each paper's method is a black box and
the adapter only renames/reshapes I/O at the boundary. That holds only
when papers are genuinely interchangeable on a shared task (e.g. GENI vs.
a closed-form link predictor).

But the valuable PaperLab comparisons are not like that. When two papers
share a **principle** (the information bottleneck) and differ in a
**mechanism inside it** (the bottleneck sampling/selection step), the
thing to compare is the *internal divergence point*, not the whole
method. Black-box wrapping either measures the wrong thing (task-setup
differences instead of the mechanism) or is impossible (no shared task
signature). The real experiment holds the principle + task fixed and
swaps only the mechanism — which requires reaching *inside* each method.

## Two regimes

| | Regime 1: method-level | Regime 2: component-level |
|---|---|---|
| What's compared | whole methods on a shared task | one divergent component inside a shared principle |
| Papers | interchangeable on the task | share a principle, differ in a mechanism |
| What's built | thin adapter (rename/reshape) | shared scaffold + extracted components |
| Touches internals? | no | yes — by design |
| Example | GENI vs. closed-form link predictor | GIB vs. GIB-SR: same IB, different sampling |

The kickoff designed only for Regime 1. **Regime 2 is the target** — the
whole vault is organized around papers that share principles with tweaks
(GIB, GIB-DS, GraphVarBound, MIbound), which is exactly the Regime-2
shape. "General principle vs. specific task" is the crux: the point of
comparison is the algorithmic principle, not a specific training task.

## What survives from the kickoff log, what changes

**Survives:**
- **Per-paper code is immutable.** Stage 2 never edits `<slug>/code/`
  (Stage-1 `method.py`) or upstream code. The experiment never reaches
  back and mutates paper-bound code.
- **"Borrow, not reinvent."** The agent reuses the paper's method logic;
  it does not re-implement it. The divergent component is lifted from the
  paper's code, not rewritten.

**Changes:**
- **"Wrap, don't re-derive" — dropped.** You cannot harmonize black boxes
  from different papers; the comparison target is the principle, not a
  shared task. Replaced by **experiment-code synthesis**.
- **The "adapter" concept — replaced.** Not a thin shim; an integration
  step that composes borrowed components into a purpose-built scaffold.

## Settled design

1. **Target regime.** Regime 2 (component surgery). "Borrow not reinvent"
   + immutable per-paper code kept; "wrap, don't re-derive" dropped.

2. **Layout (keeps the shipped experimenter split).**
   - Design artifacts → vault `<vault>/experiments/<topic>/`
     (`design.md`, `findings.md`), via `vault_experiments_dir(topic)`.
   - Runnable code → repo `sandbox/experiments/<topic>/`, via
     `repo_experiments_dir(topic)`:
     ```
     sandbox/experiments/<topic>/
     ├── methods/
     │   └── <slug>/
     │       └── extracted.py   refactored/extracted component (provenance-stamped)
     ├── scaffold.py            agent-synthesized shared skeleton
     ├── run.py                 driver: synthetic data → results
     └── results/
     ```
   - Principle: experiment artifacts stay isolated from per-paper
     artifacts on both sides. No new `TopicGroups/` concept —
     `experiments/<topic>/` already isolates by topic.

3. **Borrow ladder (how a component is reused).**
   1. **Import directly** if the component is cleanly separable in the
      source (`from <paper> import <Component>`, from upstream or Stage-1
      `method.py`).
   2. **Extract-and-refactor** if entangled (e.g. bottleneck fused into a
      monolithic `forward()`): the agent refactors the original into a
      new `methods/<slug>/extracted.py` **under the topic** — never
      written back to `<slug>/code/`. The GIB-vs-variant case almost
      always lands here.

4. **Scaffold (the fixed part).** Synthesized fresh by the **coder** for
   the experiment; **no member paper is privileged as host**. It encodes
   the held-fixed principle + task and exposes **one primary pluggable
   slot** (R1c) via a `Protocol`/ABC. Sketch:
   ```python
   # scaffold.py (agent-synthesized; principle + task fixed)
   def run_experiment(data, bottleneck):
       h = encoder(data.x, data.edge_index)        # fixed
       z, reg = bottleneck(h, data.edge_index)      # ← THE SLOT (varies)
       y_hat = readout(z)                           # fixed
       loss = task_loss(y_hat, data.y) + beta * reg # fixed IB form
       return y_hat, loss
   ```

5. **Seam (where to cut).** The **experimenter co-designs the slot
   boundary with the user**, recorded in `design.md`. The seam defines
   what is held fixed vs. swapped — it *is* the scientific claim of the
   experiment, so it is an explicit design decision, not mechanical.
   Contract representation (R1b): **prose in `design.md` → coder
   formalizes it as a `Protocol` in `scaffold.py`.**

   The seam must fit the **union** of all member components' needs (if one
   variant needs `data.x` and another only `h`, the slot signature widens
   to carry both), and is bounded by what is **faithfully extractable**
   (it cannot demand inputs the original code never had at that point —
   that would be reinventing).

6. **Division of labor.** Experimenter + user decide *what to extract* and
   *where to cut*; the **coder executes** extraction + scaffold synthesis
   + runs. (Confirms kickoff Q6, generalized from "wrap" to "synthesize".)

7. **Fidelity — the integrity guarantee.** Nothing is both agent-invented
   and unchecked:

   | What | Check | Agent |
   |---|---|---|
   | **Extracted component** faithful to its source | static audit vs. `code_map.md` (primary) + `spec.md` (secondary); hard gate, retry ×2 → escalate | `critic` (new extraction-fidelity mode) |
   | …plus behavioral equivalence **when runnable** | run original vs. extracted on same synthetic input, assert match within tolerance | `coder` (executes; only when component runs standalone) |
   | **Synthesized scaffold** faithful to the shared principle | does the fixed objective/task represent what the papers claim to share | `critic` (scaffold-fidelity check) |
   | **End-to-end run** emits comparable outputs | harness runs each plugged variant on synthetic data → `results/` | `coder` runs; `evaluator` interprets (when built) |

   - The critic owns the verdict (firewalled — re-reads the paper
     independently, did not write the extraction). The coder's behavioral
     test, when available, feeds **into** the critic's verdict as
     corroborating evidence (single decision-maker, build-time detail).
   - Behavioral equivalence is opportunistic: if a component were cleanly
     runnable in isolation it could usually have been *imported* (the
     import branch), so it is a bonus, not the gate.
   - R1d: the scaffold is agent-invented and encodes a claim ("this is the
     shared IB objective"); a wrong scaffold loss measures both methods
     under a wrong objective, so it gets its own critic check.

8. **Provenance.** `extracted.py` carries a header recording source paper
   / file / lines and "extracted/refactored, not original." Slug-based
   naming where it disambiguates (`methods/GIB/extracted.py`, class
   `GIBBottleneck`).

9. **Failure surfacing (no silent drops).**
   - **`design.md`** — a planned extraction that proves infeasible at
     design time, or two papers that cannot share a faithful seam, is
     logged as a known limitation of the comparison.
   - **`findings.md`** — a failure during run/audit (critic keeps failing
     an extraction after retries; a variant won't run) becomes a row, so
     the result set honestly reflects what was and wasn't compared.

## Worked example (GIB vs. GIB-SR)

Both apply the information bottleneck to graph node classification —
minimize $I(X; Z) - \beta I(Z; Y)$ — and diverge in how they realize the
bottleneck (GIB: reparameterized Gaussian noise on node embeddings;
GIB-SR: structural/subgraph sampling). Experiment question: holding the
IB objective and the node-classification task fixed, which
bottleneck-sampling gives better accuracy?

The three difficulties of the seam:
- **Seam location.** Is the regularizer term $\hat{I}(X;Z)$ inside the
  slot or fixed in the scaffold? If the papers compute it differently *as
  part of their sampling*, it belongs in the slot — fixing it would force
  one paper's regularizer on the other and invalidate the comparison.
- **Union of needs.** If GIB-SR's sampling needs raw `data.x` but GIB only
  needs `h`, the slot signature widens to `(h, x, edge_index)` even though
  GIB ignores `x`.
- **Faithful extractability.** If GIB injects noise *during* message
  passing (fused into `forward()`), producing a post-encoder `z` requires
  refactoring that must preserve computation order — exactly where the
  extract-and-refactor branch and the critic fidelity gate engage.

## R3 — build-scoping bridge (the plan for the build session)

Not a design decision; the concrete file-change list:

- **`.cursor/skills/ml-experiment-code/SKILL.md` § STAGE 2** — full
  rewrite. Currently describes black-box wrapping; becomes extraction +
  scaffold synthesis: the borrow ladder, the slot/`Protocol` contract,
  the layout, the self-checks.
- **`.cursor/skills/ml-critique/SKILL.md`** — new
  extraction-fidelity + scaffold-fidelity audit mode (`code_map.md`
  primary / `spec.md` secondary; hard gate, retry → escalate).
- **`.cursor/agents/coder.md`** — adapt-mode redefined: synthesize
  `scaffold.py`, produce `methods/<slug>/extracted.py`, run
  behavioral-equivalence when feasible, run the harness.
- **`.cursor/agents/experimenter.md`** — seam co-design with the user,
  invoke the critic gate, invoke the coder, route the user-check gate
  (Seam B).
- **Docs** — `AGENTS.md`, `ROADMAP.md`; mark the kickoff log superseded by
  this one.

## Open at build time (deliberately deferred)

- How the two fidelity layers compose mechanically (critic-owns-verdict
  vs. independent gates) — leaning critic-owns-verdict.
- Exact `Protocol` shape per topic (emerges from the first real seam).
- Whether more than one slot is ever allowed (default: one primary slot).
- Sequencing vs. the `evaluator`: smoke-test Stage 2 to "results emitted"
  before the evaluator exists, or pair them for a first end-to-end run.

## Resume block

> Resuming the Stage-2 coder redesign. Read
> `log/2026-06-04-stage2-regime2-component-surgery-design.md` (full
> settled design) and its predecessor
> `log/2026-06-04-stage2-coder-adapt-kickoff.md` (superseded Regime-1
> framing). The design is settled through R1–R3; next is the build
> session per the R3 file-change list. Discuss before building; do not
> rush into building.
