# 2026-06-17 — GIBGAT Stage-2 extension-regime mechanical re-validation

Mechanical re-validation of the Stage-2 **extension regime** shipped
2026-06-16 ([`log/2026-06-16-critic-code-review-and-coder-extension.md`](./2026-06-16-critic-code-review-and-coder-extension.md))
against the in-flight GIBGAT planted-signal experiment under
`sandbox/experiments/gib-importance/`. Single-method exploratory probe
(`design.md` `research_type: exploration`).

This was scope option **B (mechanical)** of the smoke-test menu —
restructure the experiment to the new spec and exercise the coder /
critic code paths. Scope option **A2 (behavioral)** — a fresh
`/experimenter <topic>` chat that drives the production flow end to
end — is **not** done by this log; it is the next session's job.

## What changed

### Layout

Old (improvised pre-2026-06-16):

```
sandbox/experiments/gib-importance/methods/
├── extended_gibgat.py    (~360 LoC, hand-rolled)
└── vault_import.py       (importlib loader)
```

New (per 2026-06-16 extension-regime spec):

```
sandbox/experiments/gib-importance/methods/
└── gibgat/
    ├── _vault_import.py  (importlib loader, moved + parents[5])
    └── extended.py       (~280 LoC, inherits Stage-1 GIBGATLayer / Method)
```

`extended_gibgat.py` and `vault_import.py` deleted. `__pycache__/` cleaned.

### Inheritance

- `ExtendedGIBGATLayer(GIBGATLayer)` — overrides only `__init__` (widens
  `self.att` from `[max_hop, heads, 2*F]` to `[max_hop, heads, 2*F + 1]`
  for the scalar edge feature in the candidate logit), `_structure_and_pool`
  (threads `edge_index` / `edge_attr` and emits per-directed-edge AIB-Bern
  KL telemetry), and `forward` (signature change). `_transform`,
  `_gaussian_sample`, `MixtureGaussianPrior`, `_bernoulli_kl` are
  inherited from the audited Stage-1 `method.py`, not re-implemented.
- `ExtendedGIBGAT(Method)` — calls `super().__init__(struct_mode="bern", …)`
  to inherit state setup, then **replaces** `self.layers` with
  uniform-width edge-aware variants and adds `self.graph_head` for the
  graph-level readout. `forward` is overridden for the
  graph-classification I/O contract: returns
  `(graph_logits, reg_info, per_edge_kl, per_node_ixz)` instead of the
  base node-level `(h, reg_info)`.

The two model-level overrides correspond exactly to the two extensions
declared in `design.md` §5.1: graph-level readout (sum-pool + linear
head) and edge-feature-aware attention. No silent base-method drift.

### Other edits

- `run/train_and_recover.py`: import paths (`methods.extended_gibgat` →
  `methods.gibgat.extended`; `methods.vault_import` →
  `methods.gibgat._vault_import`); plus the batch-mean fix (see below).
- `README.md`: layout block updated; the old "custom one-off (no §5.2
  seam, no critic extraction-fidelity gate)" caveat replaced with a
  pointer to the extension regime.

## Critic extension-fidelity gate — PASS

Spec: `.cursor/skills/ml-critique/SKILL.md` § "Extension-fidelity mode".

**Verdict: PASS** with three `[PROVENANCE-GAP]` warnings (warnings do
not flip the verdict).

### Invocation

The gate is documented as `experimenter`-invoked, never user-invoked.
Here the user explicitly authorized the **main chat agent** to invoke
the critic directly so the gate logic could be exercised before the
production hand-off (option A1 in the chat menu). The critic was
asked to flag this in its hand-off note; it confirmed the spec is
followable from this irregular invocation path. The full
`/experimenter`-driven flow is still untested — see "Open follow-ups".

### Findings honored

The PASS-with-warnings verdict was acted on as follows:

- **Warning 3 (batch-mean) — fixed in this session.** `design.md` §5.1
  says AIB/XIB are "summed over nodes/edges within each graph and
  averaged across the batch." `compute_loss` was summing the batch
  sums (`sum(structure_kl_list)`) and taking
  `.mean()` over the union-of-nodes tensor. Now divides by
  `batch.num_graphs`. Smoke re-run after the change still passes
  (`test_accuracy=1.0` on 5 epochs / 10 graphs).
- **Warning 1 (`GATConv` vs hop-pool)** — *parked.* `design.md` §5.1
  mentions a `GATConv(..., edge_dim=1)` implementation; actual code
  uses Stage-1's hop-pool loop with a widened `att`. The math is
  identical (`(Z̃_v ⊕ e_{vu} ⊕ Z̃_u) a^T` and per-candidate Bernoulli
  KL), only the implementation vehicle differs, and reusing Stage-1's
  hop-pool path is the inheritance the spec actually wants. Treated
  as documentation hygiene, deferred.
- **Warning 2 (thin per-override provenance)** — *parked.* Module
  docstring cites `design.md` and the 2026-06-16 log; per-override
  `code_map.md §` / `spec.md §` anchors are still missing. Future
  cleanup pass.

### Smoke runs

- Pre-fix: smoke passed, layout switch validated.
- Post-fix (batch-mean): smoke passed, behaviour delta is the
  expected `/num_graphs` rescale of the IB terms.

In both cases: imports resolve through the new `methods/gibgat/`
package; vault `method.py` loads via `tools.paths.vault_code_dir`;
forward + backward + recovery evaluation complete; JSON output
written. Recovery numbers are not interpretable at 5 epochs / 10
graphs (design spec is 2000 epochs / 200 graphs); smoke is purely a
pipeline check.

## Files touched

Created:

- `sandbox/experiments/gib-importance/methods/gibgat/_vault_import.py`
- `sandbox/experiments/gib-importance/methods/gibgat/extended.py`

Modified:

- `sandbox/experiments/gib-importance/run/train_and_recover.py`
  (import paths + batch-mean fix per `design.md` §5.1)
- `sandbox/experiments/gib-importance/README.md` (layout block)

Deleted:

- `sandbox/experiments/gib-importance/methods/extended_gibgat.py`
- `sandbox/experiments/gib-importance/methods/vault_import.py`

Vault: no writes. The `critic_reviews.md` / `code_review.md` split
flagged in the 2026-06-16 log was already migrated by the time this
session started; the open migration question listed there
("Migrate or leave as one-off?") is **resolved** — already migrated.

## Open follow-ups

1. **A2 — production-flow re-validation.** The next session should
   open a fresh `/experimenter gib-importance` chat and drive it
   through Plan phase to Build phase, observing whether the
   "Implement hand-off split by member count" routes to the extension
   regime (single member = GIBGAT) and whether the critic gate fires
   correctly without manual coaching. This is the smoke test the
   2026-06-15 log and the 2026-06-16 design called for as their
   final validation step. Until A2 runs, the production hand-off
   path is *not* re-validated; only the gate logic is.
2. **Provenance hygiene (warnings 1 + 2).** Add per-override
   `code_map.md §` / `spec.md §` anchors in `extended.py` and
   `train_and_recover.py`, and a comment noting the deliberate
   non-use of `GATConv`. Cosmetic; not blocking.
3. **`design.md` §5.1 prose update.** Either (a) edit the design to
   replace the `GATConv(..., edge_dim=1)` mention with the hop-pool
   reuse story, or (b) leave the mention as historical and let the
   extended.py docstring own the implementation note. User's call.
4. **`design.md` §8 uncertainty flag.** The flag *"⚠️ UNCERTAIN: The
   exploratory-probe schema variant (no §5.2 seam) is a permitted but
   lightly-used shape; downstream agents (`coder` Stage 2,
   `evaluator`) have so far been driven by methods-comparison
   designs. Component-surgery may not be the right Stage-2 mode for
   this experiment; a single-method 'implement, train, instrument,
   dump scores' pipeline is closer."* is now **resolvable** — the
   2026-06-16 extension regime is exactly what it asked for, and
   this session demonstrates the regime works for it. Remove or
   downgrade this flag in a separate edit pass once A2 confirms.
5. **`evaluator`** is still not built, so this experiment will run
   to "results emitted" only, same stop boundary as every other
   Stage-2 experiment.
