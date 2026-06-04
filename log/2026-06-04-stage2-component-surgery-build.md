# 2026-06-04 — Stage 2 component surgery: build session

Build session (Agent mode). Implements the design settled in
[`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./2026-06-04-stage2-regime2-component-surgery-design.md)
(the R3 file-change list). No code was *run*; this is a prompts/skills
build (agent + skill markdown). Smoke test deferred.

## Scope chosen

The user picked the **minimal wire** for the experimenter (option 2 of the
build-scope fork): land the load-bearing `design.md` §2b seam section plus
a short experimenter hand-off to the coder Stage 2, and defer the full
implement/run orchestration protocol to a follow-up. The three core files
(skill Stage 2, coder, critic) were built in full.

## Files changed

1. **`.cursor/skills/ml-experiment-code/SKILL.md`** — § STAGE 2 fully
   rewritten from the black-box "wrapping/adapter" placeholder into
   **component surgery**: the two-regime framing, settled principles,
   inputs (seam contract + `code_map.md`/`spec.md` + source), the
   `repo_experiments_dir(topic)` file layout (`scaffold.py`,
   `methods/<slug>/extracted.py`, `run.py`), the scaffold-contract
   `Protocol`, the borrow ladder (import-direct / extract-and-refactor),
   the provenance header, the three fidelity gates, the process,
   self-checks, scope boundaries. Front-matter + top diagram updated.
2. **`.cursor/agents/coder.md`** — Stage-2 description, invocation
   (backend, experimenter-invoked; no longer "not built"), a Stage-2
   process section, Stage-2 reporting, and Stage-2 scope boundaries.
3. **`.cursor/skills/ml-critique/SKILL.md`** — new **extraction-fidelity
   mode** section (Check A per-paper extraction vs. `code_map.md`; Check B
   scaffold vs. shared principle; behavioral-equivalence evidence from the
   coder; verdict rules `[EXTRACTION-DRIFT]` / `[SCAFFOLD-DRIFT]` fail,
   `[PROVENANCE-GAP]` / `[UNVERIFIABLE]` warn; per-paper PASS/FAIL).
   Front-matter updated.
4. **`.cursor/agents/critic.md`** — extraction-fidelity mode added to
   role/scope, invocation, and a process + reporting section.
5. **`.cursor/skills/ml-experiment-design/SKILL.md`** — new **§2b
   Comparison seam** in the `design.md` schema (held-fixed principle +
   task, the pluggable slot with union I/O, per-method divergent component
   + `code_map.md` source); lifecycle §3 implement/run updated from
   "pending the coder" to "Stage 2 built, hand-off wired"; a §2b
   self-check row.
6. **`.cursor/agents/experimenter.md`** — a §2d-bis seam co-design step,
   an "Invoking the coder (Stage 2)" section (seam → coder → critic gate →
   Seam-B user-check), the "stop at implement boundary" §4 turned into an
   "implement hand-off" §4, and the scope-boundary line updated.
7. **`ROADMAP.md`** — coder row (Stage 2 shipped), critic row
   (extraction-fidelity mode), experimenter row (Stage-2 hand-off wired),
   build-order line, the experimenter-suite §3 coder bullet, the
   "what's currently working" reference, and the skills line.
8. **`AGENTS.md`** — experimenter-suite status line, coder Stage-2
   paragraph, experimenter bullet, critic gate-modes sentence, and the
   agent→skill mapping line for the coder.

## What is and isn't done

**Done:** Stage 2 is fully *specified* end-to-end in the skills + agents —
a coder run, given a seam, knows how to synthesize the scaffold, extract
components, stamp provenance, and run; the critic knows how to gate it;
the experimenter knows how to drive the hand-off. Docs reflect "shipped."

**Not done (deferred):**
- **Full implement/run orchestration protocol** in the experimenter
  (the minimal wire gives the hand-off + gate routing, not a fleshed-out
  multi-turn run loop).
- **Smoke test.** No real experiment was run. The intended first smoke
  test (per the design log) is a GIB-family component-surgery experiment,
  or the kickoff's GENI-to-minimal-harness path, run to "results emitted."
- **`evaluator`** is still unbuilt, so `findings.md` has no writer — an
  experiment can reach results, not an interpreted write-up.
- **Path-resolution backfill** for the experimenter/coder reading vault
  code (ROADMAP Known-limitation "Agents must resolve out-of-workspace
  vault code via the CLI"): the Stage-2 skill/agent instruct `code-dir
  <slug>` resolution, but this hasn't been validated on a live run.

## Lint note

`ReadLints` reports ~115 markdownlint **warnings** across the touched
files (MD025 multiple-H1, MD040 code-fence language, MD060 table spacing,
etc.). All are pre-existing repo-wide style conventions the project does
not follow — present in the untouched Stage-1 sections and existing
tables too — not defects introduced here. Left as-is to avoid churn.

## Next session

Smoke-test the chain on a real topic (GIB family), and/or flesh out the
experimenter's full implement/run loop, then build the `evaluator`.
