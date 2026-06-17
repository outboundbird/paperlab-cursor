# PaperLab Roadmap

Status as of 2026-06-16. Living document — items move between sections as their status changes.

## File layout contract

Two locations, clean split: **code and source material in the repo, agent-generated notes in the vault**.

### Repo (`paperlab-cursor/`)

```
paperlab-cursor/
├── .cursor/                       agents, skills, rules
├── papers/
│   └── <slug>/
│       ├── <slug>.pdf             paper PDF (large; git-ignored)
│       ├── supplementals/         appendices, supplementary PDFs
│       └── upstream/
│           └── <slug>/            cloned official git repo
├── sandbox/
│   └── <slug>/                    toy experiments
├── paperlab.config.yaml           per-machine, git-ignored
├── paperlab.config.example.yaml   committed template
├── AGENTS.md
├── ROADMAP.md
└── README.md
```

### Vault (Obsidian)

All agent-generated files live flat under one folder per paper:

```
<vault_paperlab_path>/
└── <slug>/
    ├── paper-info.md
    ├── spec.md
    ├── code_map.md
    ├── critic_reviews.md          critic: official-source audit (when code_map.md source is `official`)
    ├── code_review.md              critic: reconstructed-source audit (when code_map.md source is `reconstructed`; sibling, same schema)
    ├── tutor_log.md               tutor: per-turn breadcrumb log (append-only)
    ├── tutor_notes.md             tutor: curated study notes (user-triggered)
    ├── <concept>.md               tutor-written (final, user-facing)
    ├── <concept>-<slug>.md        explainer-written (backend intermediate)
    ├── synth__<a>__<b>.md         tutor-written (final, user-facing)
    ├── synth__<a>__<b>-<slug>.md  explainer-written (backend intermediate)
    ├── code/                      coder Stage-1 runnable method code (see note)
    │   ├── method.py              hybrid Method interface; paper-natural guts
    │   ├── test_invariants.py     blueprint §4 invariants as runtime asserts
    │   └── README.md              optional bare run-stub (NOT a walkthrough)
    └── notes.md                   user notes
```

**Exception to the code/notes split (2026-06-04):** the `coder`'s Stage-1 output is the one place runnable `.py` lives in the **vault** rather than the repo. Rationale: this per-paper method code is reusable, user-reviewable, and git-tracked alongside the notes it is derived from. It is contained — a dedicated `code/` subfolder (`vault_code_dir(slug)`), and the post-hoc verifier hook is scoped to `.md` so it ignores this code (which is guarded instead by its own invariant assertions). Everything else still obeys "code and source material in the repo, agent-generated notes in the vault."

The algorithm↔code **walkthrough** for reconstructed code is **not** in `code/` — it is the implementer's `code_map.md` (the `reconstructed` source; the same artifact official-code papers get), audited by the critic against `spec.md` ([`log/2026-06-04-codemap-from-coder-critic-audit.md`](./log/2026-06-04-codemap-from-coder-critic-audit.md)). This keeps one walkthrough format/author and keeps documentation off the code's author (the coder).

Current `vault_paperlab_path` (work machine): `C:/Users/e0482362/OneDrive - Sanofi/Workspace/Topics/public/Modeling/PaperLab` (ASCII-only — see Known limitations for why).

### Cross-references

- `paper-info.md` in the vault contains **absolute** links to the repo-side PDF and upstream code, constructed from `repo_root` in `paperlab.config.yaml`.
- Absolute paths differ per machine. `paperlab.config.yaml` is per-machine and git-ignored. Each machine carries its own copy.

### Unified file convention

- One schema. No agent-only or user-only file variants.
- On regeneration of an existing file, agents MUST ask: **replace**, **append**, or **abort**. See `.cursor/rules/paperlab-regenerate-prompt.mdc`.
- All paper folders follow the same flat structure. No per-paper config files.

## Agents

Living table of all subagents in the project. Update whenever an agent ships, is parked, or changes role.

| Agent | Status | Skill(s) | Role | Invocation cue |
|---|---|---|---|---|
| `acquirer` | Shipped (auto-chain 2026-05-29) | `ml-acquisition` | Set up per-paper repo + vault folders; download PDF / supplements; clone upstream; write `paper-info.md`. Two modes: `acquire <slug> <url>` (new) and `rerun <slug>` (refresh existing to current schema). On success (PDF present) auto-chains to `dissector` via the `dissect_on_acquire` hook — no user input. | User: "acquire / add / initialize / download paper `<slug>`" or "rerun `<slug>`" |
| `dissector` | Shipped (LaTeX-gated 2026-05-29) | `ml-paper-spec` | Read `<slug>.pdf`; write `spec.md` (structured extraction). Runs an **inline LaTeX gate** (latex-verifier Mode A, fix → retry ×2 → disclose) before reporting. Auto-invoked by `acquirer` after a successful acquire; carries implicit replace authorization for `spec.md`. | User: "dissect / parse / summarize / spec paper `<slug>`" (or automatic after acquire) |
| `implementer` | Shipped (+ blueprint mode 2026-06-03; two-source mapping 2026-06-04) | `ml-code-map` (+ `DEEP_DIVE`), `ml-blueprint` | Map paper concepts to a concrete implementation; write `code_map.md` or deep-dive `code_map__<slug>__<component>.md`. **Two sources, one schema:** `official` (`repo_upstream_dir`) or `reconstructed` (the coder's `vault_code_dir/method.py`); for reconstructed, re-derive from `spec.md` + `method.py`, not its own blueprint (firewall). **Blueprint mode** (explicit, opt-in): when no official code exists, reconstruct `code_blueprint.md` (`status: blueprinted`) from the paper's math, gated pre-emission by the `critic` (draft as payload → retry ×2 → escalate; write on PASS). | User: "map / annotate `<slug>`" (either source); "blueprint / reconstruct `<slug>`" |
| `critic` | Shipped (+ blueprint-check 2026-06-03; reconstructed-source audit 2026-06-04; extraction-fidelity 2026-06-04; **code_review.md split + extension-fidelity 2026-06-16**) | `ml-critique` | Audit claims, reproducibility, paper↔code alignment. **Source-adaptive output file** (changed 2026-06-16): `official` → `critic_reviews.md` (author-choice + upstream/dataset reproducibility); `reconstructed` → `code_review.md` (sibling, same schema; fidelity audit, reconstruction-drifts-from-paper + fidelity reproducibility rows = the firewalled **hop-2-vs-spec** check). **Blueprint-check mode** (backend, invoked by `implementer`): audits a draft `code_blueprint.md` pre-emission; PASS/FAIL, no file = the **hop-1** guard. **Extraction-fidelity mode** (backend, invoked by `experimenter`): pre-run gate on Stage-2 component surgery (multi-method) — Check A audits each `extracted.py` vs. its `code_map.md` source (per-paper hard gate), Check B audits `scaffold.py` vs. the shared principle; PASS/FAIL, no file. **Extension-fidelity mode** (backend, invoked by `experimenter`, added 2026-06-16): pre-run gate on Stage-2 extension regime (single-method) — audits `extended.py` and `run.py` against the audited Stage-1 `method.py` / `code_map.md` for unauthorized base-method rewrites, scope drift, or wiring drift; PASS/FAIL, no file (no scaffold). All four gate modes are the firewalled generator/discriminator check. See `log/2026-06-16-critic-code-review-and-coder-extension.md`. | User: "audit / critique / review `<slug>`" (either source); (backend) invoked by `implementer` (blueprint-check) or `experimenter` (extraction-fidelity, extension-fidelity) |
| `tutor` | **Shipped (2026-05-27)** | `ml-tutor` (+ `ml-explanation`, `ml-synthesis` when writing concept / synthesis files) | User-facing conversational tutor. Anchored to one paper at a time; paper-grounded + field-grounded; persistent memory via `tutor_log.md`. Invokes `explainer` in the background when paper-bound content is missing. Writes `tutor_log.md` (every turn), and on explicit user request `tutor_notes.md`, `<concept>.md`, `synth__<a>__<b>.md`. | User: `/tutor <slug>` or `/tutor` to resume the most recent session |
| `explainer` | **Backend-only (2026-05-27)** | `ml-explanation`, `ml-synthesis` | Invoked by `tutor`, not by the user. Writes paper-bound intermediates `<concept>-<slug>.md` and `synth__<a>__<b>-<slug>.md` for the tutor to consume. | (Internal — invoked by `tutor`) |
| ♻️ ~~`visualizer`~~ | **Exported to independent project (2026-06-05)** | (archived) | ~~Concept-picture generator.~~ Spun out of PaperLab as a standalone project; archived on branch `visualizer` and tag `archive-visualizer-2026-05-27`. See `visualizer-todo.md`. | (Not in this project) |
| ♻️ ~~`figure-verifier`~~ | **Exported to independent project (2026-06-05)** | (never authored) | ~~Pass/fail check on rendered figures.~~ Part of the exported visualizer project. | (Not in this project) |
| `prerequisite` | **Parked (2026-06-05)** | `ml-prerequisites` (parked) | Scan `spec.md`; detect assumed background; cross-check vault coverage; produce prereq graph + on-demand primers (delegates to `tutor`) | (Parked — do not invoke) |
| `experimenter` | **Converted to skill + command (2026-06-15)**; **smoke-validated 2026-06-15/16** (GIBGAT planted-signal study); **extension-regime mechanically re-validated 2026-06-17** on GIBGAT (critic extension-fidelity gate PASS; production-flow A2 smoke pending — see [`log/2026-06-17-gibgat-extension-regime-revalidation.md`](./log/2026-06-17-gibgat-extension-regime-revalidation.md)); conversational rewrite shipped 2026-06-09; design-phase shipped (2026-06-02); Stage-2 coder hand-off wired (2026-06-04, minimal); **extension-regime branch added 2026-06-16** | `experimenter` (behavior), `ml-experiment-design` (schema) | User-facing **pair-designer** for empirical experiments built around one or more papers. **Loaded as a skill via `/experimenter` command** — runs in the main chat agent (no subagent relay). **Plan phase** (default): open prose dialogue, no `AskQuestion` / multiple-choice menus, no presumption of research type. **Build phase** (user-triggered): write `design.md`, invoke `coder` Stage 2, route the critic gate + user-check, run to **results emitted**. Two regimes by member count: **component surgery** (≥ 2 papers, with the §5.2 seam contract, gated by extraction-fidelity + Seam-B user-check) and **extension regime** (exactly 1 paper, with §5.2-variant extension scope, gated by extension-fidelity; added 2026-06-16). Owns experiment + data-synthesis *design*. Notes → `<vault>/experiments/<topic>/`; code/data → `sandbox/experiments/<topic>/`. Full implement/run orchestration protocol still being fleshed out; `findings.md` awaits the `evaluator`. | User: `/experimenter <topic>` |
| `comparator` | **Shipped (2026-05-29)** | `ml-comparison` | **Conceptual** cross-method comparison from `spec.md` (+ `code_map.md` / PDF when needed) along a user-chosen axis; may refine a vague axis via propose-and-confirm. **Dual-mode:** standalone (user) or design-phase input (invoked by `experimenter`). Writes `comparison.md` under `<vault>/experiments/<topic>/`, verified by an inline LaTeX + citation gate. Carries the critic's `[A]`/`[B]` inference discipline. | User: "compare methods for `<topic>`" or (backend) invoked by `experimenter` |
| `coder` | **Stage 1 shipped 2026-06-04**; **Stage 2 component surgery shipped 2026-06-04**; **Stage 2 extension regime shipped 2026-06-16** | `ml-experiment-code` (Stage 1, Stage 2 component surgery, Stage 2 extension all shipped) | The only agent that writes **runnable code**, two stages (design [`log/2026-06-03-two-stage-coder-design.md`](./log/2026-06-03-two-stage-coder-design.md)). **Stage 1 (user-invokable):** for one paper, write reusable method code to `vault_code_dir(slug)` (`<vault>/<slug>/code/`: `method.py` + `test_invariants.py`) from `code_blueprint.md` (primary, no code) or a reimplementation of mapped upstream code. Hybrid `Method` interface; runs the blueprint's §4 invariants as runtime asserts = **hop-2-vs-blueprint guard**. Does **not** write a walkthrough — the implementer maps `method.py` into `code_map.md` afterward, critic audits it (hop-2-vs-spec). **Stage 2 (backend, invoked by `experimenter`):** two regimes picked by `design.md` member count. **Component surgery (≥ 2 papers, multi-method):** from the §5.2 seam, synthesize a shared scaffold (principle + task fixed, pluggable slot `Protocol`) and extract each paper's divergent component into `repo_experiments_dir(topic)/methods/<slug>/extracted.py` via the borrow ladder (import-direct / extract-and-refactor); NOT black-box wrapping; gated by extraction-fidelity. Design: [`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./log/2026-06-04-stage2-regime2-component-surgery-design.md). **Extension regime (exactly 1 paper, single-method, added 2026-06-16):** no scaffold, no slot — inherit / compose the audited Stage-1 `method.py` into `repo_experiments_dir(topic)/methods/<slug>/extended.py` (must not copy or hand-reimplement the base); plus `synth/generate.py` and `run.py`; gated by extension-fidelity. Used for ablations, sensitivity sweeps, planted-signal probes. See `log/2026-06-16-critic-code-review-and-coder-extension.md`. | User: `/coder code <slug>` (Stage 1); (backend) invoked by `experimenter` (Stage 2, both regimes) |
| `evaluator` | Designed (2026-05-29) | `ml-evaluation` (planned) | **Backend-only.** Interprets empirical run outputs; communicates only through `experimenter`. | (Internal — invoked by `experimenter`) |

## Decision framework: agent vs. skill vs. rule vs. hook vs. MCP

Recorded so future-us doesn't re-derive it.

1. Needs access outside the repo (API, DB, external file)? → **MCP**.
2. Should run automatically on events, deterministically? → **Hook**.
3. Is a *role* with judgment, multi-step? → **Subagent** (typically uses skills + MCPs).
4. Is *reference material* loaded on demand for specific tasks? → **Skill**.
5. Is an always-on (or glob-scoped) *constraint or convention*? → **Rule**.

Litmus tests:

- Skill vs. Rule: needed *sometimes* (skill) or *always when touching matching files* (rule)?
- Skill vs. Subagent: *how to do it* (skill) vs. *thing that does it* (subagent)?
- Subagent vs. Hook: needs *judgment* (subagent) vs. *deterministic reaction* (hook)?
- MCP vs. nothing: a shell + `Read` won't cut it? → MCP.

Anti-pattern: building a subagent for a deterministic transformation. Use a hook or script.

## Planned units

Build order is top-to-bottom. Each unit lists the primitive(s) it requires.

### 1. Experimenter suite — `experimenter` + `comparator` + `coder` + `evaluator`

**Designed 2026-05-29; `comparator` shipped 2026-05-29.** Full decision
log and rationale in
[`log/2026-05-29-experimenter-design.md`](./log/2026-05-29-experimenter-design.md).
Re-scoped from the original single-paper `ml-sandbox` framing into a
**multi-paper, problem-type-oriented, full-lifecycle** comparison suite.
The previously-parked `comparator` is un-parked and folded in here.

- **Four agents:**
  - `experimenter` (user-facing orchestrator, **designed**) — interactive design + data-synthesis decisions; small in-session code tweaks; discusses results. Skill: `ml-experiment-design`.
  - `comparator` (dual-mode, **shipped 2026-05-29**) — conceptual method comparison from specs along a user-chosen axis. Skill: `ml-comparison`. See "Recently completed" for build notes.
  - `coder` (**Stage 1 shipped 2026-06-04**; **Stage 2 shipped 2026-06-04**) — the only agent that writes runnable code, split two ways (design [`log/2026-06-03-two-stage-coder-design.md`](./log/2026-06-03-two-stage-coder-design.md)). **Stage 1 (standalone, per-paper, user-invokable):** blueprint or mapped-upstream → reusable, invariant-validated method code in the **vault** at `vault_code_dir(slug)`, validated by emitting the blueprint's §4 invariants as runtime asserts (hop-2 guard). **Stage 2 (component surgery, backend, invoked by `experimenter`):** synthesize a shared scaffold holding the principle + task fixed, extract each paper's divergent component into `repo_experiments_dir(topic)/methods/<slug>/extracted.py`, gated by a critic extraction/scaffold-fidelity audit. NOT black-box wrapping — the kickoff's wrapping framing ([`log/2026-06-04-stage2-coder-adapt-kickoff.md`](./log/2026-06-04-stage2-coder-adapt-kickoff.md)) is **superseded** by the component-surgery redesign ([`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./log/2026-06-04-stage2-regime2-component-surgery-design.md)). The two-stage split lets a method be coded once per paper and reused across experiments. Skill: `ml-experiment-code` (both sections shipped). Original single-stage framing in [`log/2026-06-03-implementer-coder-blueprint-design.md`](./log/2026-06-03-implementer-coder-blueprint-design.md).
  - `evaluator` (backend, **designed**) — empirical results interpretation. Skill: `ml-evaluation`.
- **Interaction model — Model 3 (hybrid).** Heavy scaffold one-shot via `coder`; tight write→check→tweak loop in-session via `experimenter`. Mirrors the proven tutor/explainer split.
- **The flow:** design (experimenter ⇄ user) → method trade-offs on demand (`comparator`) → implement+run (`coder`, user-check gate between write and run) → evaluate (`evaluator`) → discuss.
- **Interactive data-design phase** (owned by `experimenter`, Seam A): what property is tested (expressivity, sample efficiency, robustness, ...); what data features stress it (size, density, noise, distribution shift); synthetic vs. small real; minimum viable comparison (metrics, baselines, seeds). The `coder` implements this design; it does not decide it.
- **File layout:** notes/design in vault `<vault>/experiments/<topic>/` (`design.md`, `findings.md`, standalone `comparison.md`); code/data in repo `sandbox/experiments/<topic>/` (`synth/`, `methods/`, `run/`, `results/`, git-ignored `data/`). `<topic>` is user-chosen; the `experiments/` namespace avoids collision with `sandbox/<slug>/`.
- **Path helpers shipped this session:** `repo_experiments_dir(topic)` and `vault_experiments_dir(topic)` in `tools/paths.py` (CLI: `exp-sandbox`, `exp-vault`).
- **`.gitignore` carve-out shipped:** `sandbox/experiments/` re-included from the blanket `sandbox/` ignore; only `sandbox/experiments/*/data/` stays ignored (code + seed committed).
- **Parked sub-decision:** a `coder` verifier gate (a future "does it run?" check analogous to the dissector's LaTeX gate) — noted, not built now.
- **Blueprint bridge (designed 2026-06-03, [`log`](./log/2026-06-03-implementer-coder-blueprint-design.md)).** When a paper has no official code, the `implementer`'s blueprint mode writes `code_blueprint.md` (a framework-agnostic contract, gated pre-emission by the `critic`'s blueprint-check); the `coder` consumes it. Two-hop fidelity: hop-1 (math → blueprint) guarded by the firewalled critic; hop-2 (blueprint → code) guarded by invariants-as-assertions. The **harness interface** (the common `fit`/`predict`-style plug all methods conform to) is owned at design time in `design.md`. Implementer blueprint mode + critic blueprint-check **shipped 2026-06-03**; coder's two modes + harness await the `coder` build.
- **Build order:** `comparator` first (dual-mode, reads only durable specs, independently testable) ✅ **done** → `experimenter` shell (design phase) ✅ **done 2026-06-02** → `coder` Stage 1 (standalone, unblocks the per-paper hop-2 smoke test) ✅ **done 2026-06-04** → `coder` Stage 2 component surgery (**not wrapping** — scaffold synthesis + component extraction + critic extraction-fidelity gate; see [`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./log/2026-06-04-stage2-regime2-component-surgery-design.md)) ✅ **done 2026-06-04** → `coder` Stage 2 extension regime (single-method, no scaffold; critic extension-fidelity gate; see `log/2026-06-16-critic-code-review-and-coder-extension.md`) ✅ **done 2026-06-16** → full implement/run orchestration + smoke test still to do → `evaluator` **next**.
- **✅ Experimenter conversational rewrite (shipped 2026-06-09; smoke-validated 2026-06-15/16).** Two `/experimenter` smoke runs (2026-06-05) showed the agent jumped straight to building on turn 1 — reads both specs, builds the comparison table, decides the seam, pops a multiple-choice menu — without asking the user a single problem-setup question. Incremental rule-patching (R0/R0a/R0b/R0c) failed twice. Diagnosis: skill + agent were *structured like a production pipeline*, so rules read as soft preferences. **Structural rewrite (2026-06-09):** (a) Plan/Build phase split — Plan is the default, conversation is the spine, schema is loaded only after user explicit confirmation; (b) `AskQuestion` and multiple-choice menus banned in Plan, allowed in Build; (c) **research type** (methods comparison, ablation, reproduction, sensitivity, exploration, custom) is an *outcome of conversation*, not an input — the agent does not presume it; (d) **kit-of-parts schema** in `ml-experiment-design` — eight sections renumbered §1–§8 (was §0/§0.5/§1/§2/§2b/§3-§7), §5 holds three subsections, §5.2 is conditional on research type; (e) **agent sketches the section list explicitly** to the user before any write; (f) the Plan→Build switch requires an explicit user signal + chat plan summary + user confirmation. Skill conversational rules (R0–R7) removed and absorbed into the agent as positive instructions. Tracked in [`log/2026-06-09-experimenter-conversational-rewrite.md`](./log/2026-06-09-experimenter-conversational-rewrite.md). **Smoke validation 2026-06-15/16:** GIBGAT planted-signal study surfaced two issues — (a) critic appended reconstructed-source audits to `critic_reviews.md` violating the regenerate-prompt rule, and (b) Stage-2 component surgery didn't fit a single-method experiment. Both fixed 2026-06-16: critic now writes `code_review.md` for `reconstructed`-source audits (sibling file) and the coder gained Stage-2 extension regime gated by a new critic extension-fidelity mode (see `log/2026-06-16-critic-code-review-and-coder-extension.md`).

### 2. External-data access

- **MCP:** reuse `firecrawl` (already configured). Add a thin `arxiv` MCP only if structured metadata becomes a recurring need.
- **Rule:** `external-fetch-budget.mdc` — max ~5 external fetches per concept; prefer arXiv abstract + 1 blog + author page; never crawl whole sites. Threshold to be tuned.

### 3. `tools.reindex` — graph index over the vault

**v1 shipped 2026-06-02.** Deterministic tool (`tools/reindex.py`) that walks the vault, parses each artifact's YAML front-matter (`paper`/`topic` + `papers`, `agent`, `status`, `sources`, `concepts`) and body `[[wiki-links]]`, and emits a queryable graph (`graph.json`) under `vault_index_dir()` (`<vault>/.index/`, a dotfolder so Obsidian ignores it). The index is a **derived cache** — rebuilt from the markdown, never hand-edited; if lost, rerun.

- **What v1 does:** nodes for papers / topics / artifacts / concepts; edges `has_artifact`, `includes_paper`, `has_status`, `derived_from` (from `sources`), `mentions` (from `concepts` + bare body wiki-links). Drift report to stderr: artifacts missing `agent`/`status`, concept names not in `.cursor/skills/concept-vocabulary.md`, and `sources` links that don't resolve to a known artifact. CLI: `python -m tools.reindex` (write) and `--check` (report only). Path helper `vault_index_dir()` added to `tools/paths.py` (CLI verb `index-dir`).
- **v1 resolved the three open questions** (per design 2026-06-02): (a) **link-only edges, no staleness hashing** — staleness needs a write-side hash stamp, deferred to v2a; (b) **concept normalization is report-only** — flags unknown names, never renames; (c) **JSON only** — no `_index.md` rollup (Obsidian's graph view already gives a human view).
- **First run (2026-06-02):** 45 nodes / 31 edges over the legacy test vault. Only `has_artifact` edges fired — the existing papers predate Phase 1, so they carry no `status`/`sources`/`concepts` and the drift report correctly flags them. Expected: the test papers were deliberately **not** backfilled. New papers acquired after Phase 1 populate the schema automatically; the richer edges light up then.
- **Why tool, not subagent?** Pure deterministic parse-and-aggregate.

#### v2 directions (need a larger paper corpus to validate)

- **v2a — Staleness detection.** Record source content-hashes at *write* time (a hook change), so reindex can flag "`comparison.md` built from `spec.md`@a3f9, now @b1c2 — stale." The original motivation; gated on the write-side stamp.
- **v2b — Agents consult the graph.** Generators query `graph.json` before reading raw files (tutor: "what concepts here, and where else do they appear"; comparator: "which papers share this concept"). Graph as a generation *input*, not just output.
- **v2c — Lifecycle queries.** "Which papers are dissected but not critiqued" as a CLI/dashboard, or driving auto-chain logic.
- **v2d — `_index.md` rollup.** Human-facing per-paper or global summary generated from the graph.
- **Bigger leap — two-memory critic loop (design captured 2026-06-02):** generators share a structured-spec working memory; critics hold a *complementary* representation (consequence lists: limits, signs, types/shapes, invariants, Markov/independence, monotonicity) and gate the working memory **pre-emission** (critic checks → retry ×2 → escalate to user; no disk write/rewrite loop). The graph's `derived_from` / `mentions` edges are the substrate a pre-emission critic needs.
  - **Partially realized (2026-06-04).** The **firewall / generator-discriminator pattern** — a critic that builds an *independent* representation and gates a generator's output pre-emission — has now shipped in **three concrete gates**: `blueprint-check` (vs. the implementer's draft blueprint), the `reconstructed`-source audit (hop-2-vs-spec), and Stage-2 `extraction-fidelity` (vs. `code_map.md` + scaffold-vs-principle). What remains **unbuilt** is the loop's distinctive *architecture*: a **persistent, standing complementary representation** (the consequence-list memory as a durable data structure) and its **wiring to the reindex graph** as substrate. The shipped gates re-derive their independent reading ad hoc per invocation and are not graph-backed. Remaining effort gated on a larger corpus; not scheduled.

## Exported to a separate project

Work that has left PaperLab to live as a standalone project.

The `visualizer` and `figure-verifier` are now an **independent project**, exported out of PaperLab; see [`visualizer-todo.md`](./visualizer-todo.md).

## Parked

Designed but deferred until the units above are stable.

### `comparator` subagent + `ml-comparison` skill — UN-PARKED 2026-05-29

Folded into the Experimenter suite (Planned units §3). Re-scoped to a
**conceptual, dual-mode** comparison agent (standalone or invoked by the
`experimenter` in the design phase). Empirical results comparison split
out into the new backend-only `evaluator`. See
[`log/2026-05-29-experimenter-design.md`](./log/2026-05-29-experimenter-design.md).

- **Original framing (for traceability):** cross-paper synthesis. Inputs N paper slugs + a comparison axis (e.g., "Graph Information Bottleneck objective formulations"). Output: `<vault>/PaperLab/comparisons/<topic>/comparison.md`. Parked because synthesis design is tricky; revisit when there are 3+ comparable papers in the vault. (The 3+-papers condition is now met across the vault.)

## Deferred features

Things explicitly deferred during design, with the reason. Each entry should be specific enough to act on without rereading the conversation that produced it.

### Two-way sync of `notes.md` between vault and repo

- **What:** if `notes.md` ever needs to be edited from outside Obsidian.
- **Why deferred:** current model is vault-only; no demonstrated need.
- **Trigger to revisit:** if user wants to add notes from a machine without the vault.
- **Estimated effort:** small.
- **Notes:** none.

## Known limitations

Things the system can't do, with workarounds where they exist.

### Repo-to-vault absolute paths break across machines

- **What:** the PDF/upstream links inside `paper-info.md` are absolute and machine-specific.
- **Why:** the paperlab repo path may differ between work and personal machines.
- **Workaround:** regenerate `paper-info.md` on each machine (cheap), or treat broken links as expected on the other machine.

### Windows: non-BMP characters in `vault_paperlab_path` break agents

- **What:** if `vault_paperlab_path` contains emoji or other non-BMP characters (`🎓`, `🤖`, `🕸️`, etc.) up to and including the `PaperLab/` segment, agents on Windows — most visibly the Tutor — loop on file-existence checks or report files as missing when they exist.
- **Why:** Windows shells (cmd.exe cp1252) and Cursor's tool-call serialization layer round-trip non-BMP characters unreliably. `tools/paths.py` forces UTF-8 stdout, which fixes resolution, but downstream `test -f` / `ls` invocations against the resolved path still fail.
- **Workaround:** keep `vault_paperlab_path` ASCII (no emoji, no non-BMP characters; spaces tolerated but discouraged). Folders elsewhere in the Obsidian vault — siblings, ancestors, per-paper children — may keep emojis freely. macOS and Linux are unaffected.
- **See:** `AGENTS.md` § "Windows path warning for `vault_paperlab_path`" and the comment block above `vault_paperlab_path` in `paperlab.config.example.yaml`.
- **Possible fix:** make `paper-info.md` use a placeholder like `{repo_root}/papers/<slug>/<slug>.pdf` that an Obsidian plugin or hook resolves at view time. Medium effort, low priority.

### Agents must resolve out-of-workspace vault code via the CLI before reading

- **What:** when an agent reads code that lives in the vault (`vault_code_dir(slug)/method.py` — the coder's reconstructed Stage-1 output), it must resolve the absolute path with `python -m tools.paths code-dir <slug>` *before* the read or existence check. Glob / relative search will not find it.
- **Why:** the vault is an Obsidian/OneDrive subtree **outside the Cursor workspace**. `official` code under `repo_upstream_dir(slug)` sits inside the workspace, so relative search happens to work there; reconstructed code does not. An agent that skips the CLI resolution sees the file as missing and (in the failure we hit on 2026-06-04) reports "no code to map" or refuses to delegate — a false negative, not a real absence.
- **Workaround / fix shipped:** `implementer.md` (source-detection + reconstructed-source navigation) and `critic.md` (reconstructed audit cross-check) now instruct the agent to resolve `code-dir <slug>` first and read from the printed absolute path. Validated end-to-end on GENI (2026-06-04): blueprint → coder `method.py` → implementer `code_map.md` (reconstructed) → critic `critic_reviews.md` (hop-2 fidelity audit). See [`log/2026-06-04-codemap-from-coder-critic-audit.md`](./log/2026-06-04-codemap-from-coder-critic-audit.md) § "Path-resolution fix + GENI validation".
- **Residual risk:** other agents that may later read vault code (`coder` Stage-2 adapt-mode, `experimenter`) carry the same blind spot until given the same instruction. Backfill when those modes ship.

## Schema improvement candidates

Small refinements to existing schemas that aren't urgent but are worth remembering. These tend to surface during use.

## Completed work

The roadmap is forward-looking. Completed-work history has moved to
[`log/changelog_history.md`](./log/changelog_history.md); per-session
decision narratives live in the dated logs under `log/`.

## Reference: what's currently working

- **Subagents (user-facing):** `acquirer`, `dissector`, `implementer`, `critic`, `tutor`, `comparator`, `coder` (Stage 1, `/coder code <slug>`).
- **Skills + commands (user-facing, inline — no subagent relay):** `experimenter` (skill at `.cursor/skills/experimenter/`, loaded by `/experimenter <topic>` command).
- **Subagents (backend-only):** `explainer` (invoked by `tutor` since 2026-05-27); `latex-verifier`, `citation-verifier` (inline gate + post-hoc hook); `coder` Stage 2 (component surgery and extension regime, invoked by `experimenter`); `critic` extraction-fidelity and extension-fidelity modes (invoked by `experimenter`); `critic` blueprint-check mode (invoked by `implementer`).
- **Skills (active):** `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-blueprint`, `ml-critique`, `ml-tutor`, `ml-explanation`, `ml-synthesis`, `ml-comparison`, `ml-experiment-design`, `ml-experiment-code` (Stage-1 + Stage-2 sections).
- **Rules:** `paperlab-config-bootstrap`, `paperlab-regenerate-prompt`.
- **Helpers:** `tools/paths.py`, `tools/figures.py` (requires `pymupdf`).
- **Papers:** `Memento` (legacy, in repo), `WorldModel`, `VAE`, `GIB-DS`, `GIB`, `GraphVarBound`, `Dreamer`, `MIbound` (new layout, vault + repo).
