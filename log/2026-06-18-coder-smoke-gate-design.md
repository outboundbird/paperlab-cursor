# 2026-06-18 — Coder smoke gate design

## Context

Stage 1 of the coder already runs `test_invariants.py` on synthetic input as
the hop-2-vs-blueprint guard, and it is bounded (3 fix attempts) and
explicitly required to pass before the agent reports success. Stage 2 has no
equivalent end-to-end runtime check before the user reads results: the
critic's extraction-fidelity / extension-fidelity audits cover *fidelity*,
but they cannot tell you that `run.py` actually executes without crashing
on the exact synthetic inputs `design.md` describes.

The **coder smoke gate** closes that loop: after the critic's fidelity
audit passes, but before declaring the Stage-2 build complete, the coder
runs `run.py --smoke` (a tiny conditioned execution path) and reports
PASS / FAIL / TIMEOUT to the experimenter. A FAIL or TIMEOUT means the
experimenter does not transition to the long-running Build-evaluate
phase; the user fixes whatever broke and re-runs.

## Approved design (all confirmed except Q9 timeout)

| Q | Decision |
|---|---|
| Q1 | Smoke is a `--smoke` flag on `run.py` (not a separate file). One condition, one seed, one batch, no checkpointing, no plotting. Exits non-zero on any unhandled exception. |
| Q2 | Timeout = FAIL. The smoke run must finish within the configured budget; a hang is treated as a failure. |
| Q3 | Smoke gate runs **after** the critic's fidelity gate passes (so we don't waste a smoke run on code the critic will reject) and **before** the coder reports back to the experimenter. |
| Q4 | Stage 1 already has its own smoke equivalent (`test_invariants.py` with a 3-attempt fix budget). The new gate applies to Stage 2 only. |
| Q5 | On FAIL: 1 retry (the coder gets one shot to fix and re-run). On second FAIL or TIMEOUT: report to the experimenter, do **not** claim success, leave the failing code in place for the user. |
| Q6 | Reporting: a single line in the coder's hand-back to the experimenter — `Smoke gate: PASS (Ns)` / `Smoke gate: FAIL (...)` / `Smoke gate: TIMEOUT (Ns)` — plus a stderr excerpt on failure. The experimenter relays it to the user verbatim. |
| Q7 | The gate skips itself with `Smoke gate: SKIPPED — extension regime, opportunistic behavioral-equivalence already covers it` only when the design explicitly says so. Default is to run it for both regimes (component surgery and extension). |
| Q8 | Stage-1 invariant timeout default 30s; Stage-2 smoke timeout default 60s. **Hardware-dependent — see Q9.** |
| Q9 | **Confirmed.** Per-machine config keys `coder_smoke_timeout.stage1` (default 30s) and `coder_smoke_timeout.stage2` (default 60s) in `paperlab.config.yaml`. New helper `coder_smoke_timeouts()` in `tools/paths.py`. Override wins; defaults assume a workstation. |

## Shipped

1. **`tools/paths.py`** — `coder_smoke_timeouts() -> tuple[int, int]`
   reads `coder_smoke_timeout.{stage1,stage2}` from `load_config()`
   with `(30, 60)` defaults.
2. **`paperlab.config.example.yaml`** — documented the keys with a
   per-machine comment explaining slow-hardware bumps.
3. **`.cursor/skills/ml-experiment-code/SKILL.md`** —
   - Stage-1 step 5 now references the timeout helper for
     `test_invariants.py`.
   - New "Stage-2 smoke gate" shared subsection under the
     component-surgery section (covers `--smoke` semantics, timeout,
     verdict + retry, skip rule).
   - Component-surgery process step 6 + self-check + report-back
     reference the gate.
   - Extension-regime process step 6 + self-check + report-back
     reference the gate (same semantics, no duplication).
4. (this log)

## Files touched

- `tools/paths.py`
- `paperlab.config.example.yaml`
- `.cursor/skills/ml-experiment-code/SKILL.md`
- `.cursor/skills/experimenter/SKILL.md` (post-review addendum)
- `log/2026-06-18-coder-smoke-gate-design.md`

## Post-review followups (applied)

1. **Tightened the `--smoke` "no pollute results/" rule.** Removed the
   self-contradiction between "must not pollute `results/`" and the
   `results/.smoke/` escape hatch; now reads "must not write to
   `results/` proper; if intermediate scratch output is unavoidable,
   write to `results/.smoke/` and remove that folder before exit."
2. **Wired the experimenter to gate Build-evaluate on the smoke line.**
   New "Smoke gate (after critic gate, both regimes)" subsection in
   `experimenter/SKILL.md` § 2: PASS/SKIPPED proceeds, FAIL/TIMEOUT
   refuses (no retry — the coder retries once on its own; the
   experimenter ends the turn so the user can fix). Pause-discipline
   subsection extended to refuse the evaluator on a FAIL/TIMEOUT
   smoke line, since stale `run/results/` would be misleading.

## Optional follow-ups (deferred)

- Promote `## Stage-2 smoke gate` to its own H1 so the extension regime
  doesn't have to back-reference across the component-surgery section.
- Note GIB `run.py` backfill obligation (`--smoke` flag does not
  exist in the existing `sandbox/experiments/GIB/run.py`).
- Rename `coder_smoke_timeouts()` → `coder_runtime_timeouts()` if the
  Stage-1 invariant-check use of the same helper feels misnamed
  (mechanical rename if pursued).
