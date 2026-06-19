# PaperLab Roadmap

Status as of 2026-06-16 (living document). **`ARCHITECTURE.md` added 2026-06-19** — file layout and decision framework moved there; see [`log/2026-06-19-architecture-md.md`](./log/2026-06-19-architecture-md.md).

## File layout contract

**For subagents:** authoritative repo/vault layout, `code/` exception, and conventions — [`AGENTS.md`](./AGENTS.md) § Where things live and § Unified file convention. **Human-oriented trees and narrative** — [`ARCHITECTURE.md`](./ARCHITECTURE.md) § File layout contract.

(Content summaries moved out of this roadmap on 2026-06-19; see [`log/2026-06-19-architecture-md.md`](./log/2026-06-19-architecture-md.md).)

Current `vault_paperlab_path` (work machine): `C:/Users/e0482362/OneDrive - Sanofi/Workspace/Topics/public/Modeling/PaperLab` (ASCII-only — see Known limitations for why).

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
| `experimenter` | **Converted to skill + command (2026-06-15)**; **smoke-validated 2026-06-15/16** (GIBGAT planted-signal study); **extension-regime mechanically re-validated 2026-06-17** on GIBGAT (critic extension-fidelity gate PASS; production-flow A2 smoke pending — see [`log/2026-06-17-gibgat-extension-regime-revalidation.md`](./log/2026-06-17-gibgat-extension-regime-revalidation.md)); **inline LaTeX gate on `design.md` (no citation gate) 2026-06-18**; conversational rewrite shipped 2026-06-09; design-phase shipped (2026-06-02); Stage-2 coder hand-off wired (2026-06-04, minimal); **extension-regime branch added 2026-06-16** | `experimenter` (behavior), `ml-experiment-design` (schema) | User-facing **pair-designer** for empirical experiments built around one or more papers. **Loaded as a skill via `/experimenter` command** — runs in the main chat agent (no subagent relay). **Plan phase** (default): open prose dialogue, no `AskQuestion` / multiple-choice menus, no presumption of research type. **Build phase** (user-triggered): write `design.md`, invoke `coder` Stage 2, route the critic gate + user-check, run to **results emitted**. Two regimes by member count: **component surgery** (≥ 2 papers, with the §5.2 seam contract, gated by extraction-fidelity + Seam-B user-check) and **extension regime** (exactly 1 paper, with §5.2-variant extension scope, gated by extension-fidelity; added 2026-06-16). Owns experiment + data-synthesis *design*. Notes → `<vault>/experiments/<topic>/`; code/data → `sandbox/experiments/<topic>/`. See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for suite orchestration. | User: `/experimenter <topic>` |
| `comparator` | **Shipped (2026-05-29)** | `ml-comparison` | **Conceptual** cross-method comparison from `spec.md` (+ `code_map.md` / PDF when needed) along a user-chosen axis; may refine a vague axis via propose-and-confirm. **Dual-mode:** standalone (user) or design-phase input (invoked by `experimenter`). Writes `comparison.md` under `<vault>/experiments/<topic>/`, verified by an inline LaTeX + citation gate. Carries the critic's `[A]`/`[B]` inference discipline. | User: "compare methods for `<topic>`" or (backend) invoked by `experimenter` |
| `coder` | **Stage 1 shipped 2026-06-04**; **Stage 2 component surgery shipped 2026-06-04**; **Stage 2 extension regime shipped 2026-06-16**; **smoke gate shipped 2026-06-18** (two-invocation flow: build hand-back → critic gate → smoke re-invocation, per-machine timeout via `coder_runtime_timeouts()`; see `log/2026-06-18-coder-smoke-gate-design.md`) | `ml-experiment-code` (Stage 1, Stage 2 component surgery, Stage 2 extension all shipped) | The only agent that writes **runnable code**, two stages (design [`log/2026-06-03-two-stage-coder-design.md`](./log/2026-06-03-two-stage-coder-design.md)). **Stage 1 (user-invokable):** for one paper, write reusable method code to `vault_code_dir(slug)` (`<vault>/<slug>/code/`: `method.py` + `test_invariants.py`) from `code_blueprint.md` (primary, no code) or a reimplementation of mapped upstream code. Hybrid `Method` interface; runs the blueprint's §4 invariants as runtime asserts = **hop-2-vs-blueprint guard**. Does **not** write a walkthrough — the implementer maps `method.py` into `code_map.md` afterward, critic audits it (hop-2-vs-spec). **Stage 2 (backend, invoked by `experimenter`):** two regimes picked by `design.md` member count. **Component surgery (≥ 2 papers, multi-method):** from the §5.2 seam, synthesize a shared scaffold (principle + task fixed, pluggable slot `Protocol`) and extract each paper's divergent component into `repo_experiments_dir(topic)/methods/<slug>/extracted.py` via the borrow ladder (import-direct / extract-and-refactor); NOT black-box wrapping; gated by extraction-fidelity. Design: [`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./log/2026-06-04-stage2-regime2-component-surgery-design.md). **Extension regime (exactly 1 paper, single-method, added 2026-06-16):** no scaffold, no slot — inherit / compose the audited Stage-1 `method.py` into `repo_experiments_dir(topic)/methods/<slug>/extended.py` (must not copy or hand-reimplement the base); plus `synth/generate.py` and `run.py`; gated by extension-fidelity. Used for ablations, sensitivity sweeps, planted-signal probes. See `log/2026-06-16-critic-code-review-and-coder-extension.md`. | User: `/coder code <slug>` (Stage 1); (backend) invoked by `experimenter` (Stage 2, both regimes) |
| `evaluator` | **Shipped 2026-06-17** (backend-only); **inline LaTeX gate on `findings.md` (no citation gate) 2026-06-18** | `ml-evaluation` | **Backend-only.** Invoked by `experimenter` during the **Build-evaluate** sub-phase. Reads `design.md` (hypotheses, criterion, metrics) + `repo_experiments_dir(topic)/run/results/*.json`; writes `findings.md` to `vault_experiments_dir(topic)/`. Five fixed sections (Header, Hypothesis ledger, Results, Threats to validity, What the user can conclude); Results follows a **per-`research_type` runbook** (methods comparison / ablation / reproduction / sensitivity / exploration / custom). Returns the path + a one-paragraph summary — **no PASS/FAIL**; the user judges. Honesty discipline `[A]` paper-anchored / `[B]` reader-inferred / `[E]` empirically grounded by *this* run is mandatory in every section past the header. On under-spec runs (smoke output, missing seeds, missing metric, errored trajectory), tags affected hypotheses `[INSUFFICIENT-RUN]` and ledger status `inconclusive` — does not refuse. Refusal is the experimenter's job (pause discipline). See [`log/2026-06-17-evaluator-build.md`](./log/2026-06-17-evaluator-build.md). | (Internal — invoked by `experimenter`) |

## Decision framework: agent vs. skill vs. rule vs. hook vs. MCP

Recorded in [`AGENTS.md`](./AGENTS.md) § Decision framework (moved 2026-06-19). Human-oriented context: [`ARCHITECTURE.md`](./ARCHITECTURE.md) § Decision framework.

## Planned units

Forward-looking only. Shipped work moves to [`log/changelog_history.md`](./log/changelog_history.md); per-agent status lives in the Agents table above. (External-data access — `firecrawl` MCP, the `external-fetch-budget` rule, and the now-parked `arxiv` MCP — graduated out of this section on 2026-06-19; see § Parked and the changelog.)

### 1. Experimenter suite — shipped 2026-06-17

All four agents (`experimenter`, `comparator`, `coder`, `evaluator`) shipped (design [`log/2026-05-29-experimenter-design.md`](./log/2026-05-29-experimenter-design.md)). **Only A2 remains:** production-flow smoke of the full `/experimenter` loop from a fresh chat (also exercises the smoke gate). See [`log/2026-06-17-gibgat-extension-regime-revalidation.md`](./log/2026-06-17-gibgat-extension-regime-revalidation.md) § Open follow-ups #1.

### 2. `tools.reindex` — graph index over the vault

**v1 shipped 2026-06-02** — deterministic vault parser emitting `graph.json` (nodes: papers / topics / artifacts / concepts; link-only edges; drift report to stderr; CLI `python -m tools.reindex [--check]`). Full detail in [`log/changelog_history.md`](./log/changelog_history.md). The forward-looking work below needs a larger paper corpus to validate.

#### v2 directions (need a larger paper corpus to validate)

- **v2a — Staleness detection.** Record source content-hashes at *write* time (a hook change), so reindex can flag "`comparison.md` built from `spec.md`@a3f9, now @b1c2 — stale." The original motivation; gated on the write-side stamp.
- **v2b — Agents consult the graph.** Generators query `graph.json` before reading raw files (tutor: "what concepts here, and where else do they appear"; comparator: "which papers share this concept"). Graph as a generation *input*, not just output.
- **v2c — Lifecycle queries.** "Which papers are dissected but not critiqued" as a CLI/dashboard, or driving auto-chain logic.
- **v2d — `_index.md` rollup.** Human-facing per-paper or global summary generated from the graph.
- **Bigger leap — two-memory critic loop (design captured 2026-06-02):** generators share a structured-spec working memory; critics hold a *complementary* representation (consequence lists: limits, signs, types/shapes, invariants, Markov/independence, monotonicity) and gate the working memory **pre-emission** (critic checks → retry ×2 → escalate to user; no disk write/rewrite loop). The graph's `derived_from` / `mentions` edges are the substrate a pre-emission critic needs. The **firewall / generator-discriminator pattern** has shipped as four ad-hoc critic gates (blueprint-check, reconstructed-source hop-2-vs-spec, extraction-fidelity, extension-fidelity) — see the `critic` row in the Agents table. What remains **unbuilt** is the loop's distinctive *architecture*: a persistent, standing complementary representation as a durable data structure, wired to the reindex graph. Gated on a larger corpus; not scheduled.

## Exported to a separate project

Work that has left PaperLab to live as a standalone project.

The `visualizer` and `figure-verifier` are now an **independent project**, exported out of PaperLab; see [`visualizer-todo.md`](./visualizer-todo.md).

## Parked

Designed but deferred until the units above are stable. *(The previously-parked `comparator` was un-parked and shipped 2026-05-29.)*

### Thin `arxiv` MCP — parked 2026-06-19

- **What:** a small MCP for structured arXiv metadata (title, authors, abstract, versions, references).
- **Why parked:** `firecrawl` + the citation-verifier's arXiv/Crossref resolvers cover current needs; no demonstrated problem.
- **Trigger to revisit:** a recurring need for clean structured arXiv metadata (e.g. acquirer auto-fill, comparator reference lists).
- **Scope guard:** metadata lookup only — not a general arXiv crawler.

## Deferred features

Things explicitly deferred during design, with the reason. Each entry should be specific enough to act on without rereading the conversation that produced it.

### Citation gate on `design.md` / `findings.md` — intentionally omitted

Deliberate design choice (settled 2026-06-18), not an unmet gap.

- **What:** `experimenter` (`design.md`) and `evaluator` (`findings.md`) gate **LaTeX only**; they run no citation gate. `comparator` (`comparison.md`, same `experiments/<topic>/` tree) gates both. The post-hoc hook skips this tree, so the inline gate is each writer's sole verification path.
- **Why:** both files compose material from upstream agents whose external citations are already gated (`spec.md`, `comparison.md`, `code_map.md`, `critic_reviews.md`). Novel external citations introduced *inside* `design.md` / `findings.md` are rare — `design.md` is built conversationally with the user, `findings.md` is anchored in run-output JSON, not literature. The LaTeX surface (metric formulas, restated equations) is non-trivial, so LaTeX is gated.
- **Trigger to revisit:** a hallucinated arXiv ID, DOI, URL, or mismatched citation metadata observed in either file in practice — then add a citation gate to the offending writer (mirror the comparator's R11). Effort: small (one skill section).
- **See:** [`AGENTS.md`](./AGENTS.md) § Verifier system; `log/2026-06-18-experimenter-evaluator-latex-gate.md`, `log/2026-06-17-evaluator-experimenter-gaps.md`.

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
- **Residual risk — resolved 2026-06-19:** the other agents that read vault code now carry the instruction. `coder` Stage 2 resolves via `code-dir <slug>` before reading in **both** regimes — component surgery (`coder.md`, `ml-experiment-code`) and extension regime (caveat backfilled 2026-06-19 so both regimes read identically). `experimenter` has no blind spot: it never reads vault code (Plan phase forbids it; Build phase delegates code to the `coder`). See [`log/2026-06-19-roadmap-citation-gate-notes-cleanup.md`](./log/2026-06-19-roadmap-citation-gate-notes-cleanup.md).

## Schema improvement candidates

Small refinements to existing schemas that aren't urgent but are worth remembering. These tend to surface during use. *(None currently open — the 2026-06-18 `ml-evaluation` refinements shipped and moved to [`log/changelog_history.md`](./log/changelog_history.md).)*

## Completed work

The roadmap is forward-looking. Completed-work history has moved to
[`log/changelog_history.md`](./log/changelog_history.md); per-session
decision narratives live in the dated logs under `log/`.

## Reference: documentation

- [`README.md`](./README.md) — quick start and documentation map.
- [`AGENTS.md`](./AGENTS.md) — **authoritative** subagent and skill contracts (paths, YAML, verifier, sandbox).
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — human-oriented orchestration overview (not normative for agents).

## Reference: what's currently working

- **Subagents (user-facing):** `acquirer`, `dissector`, `implementer`, `critic`, `tutor`, `comparator`, `coder` (Stage 1, `/coder code <slug>`).
- **Skills + commands (user-facing, inline — no subagent relay):** `experimenter` (skill at `.cursor/skills/experimenter/`, loaded by `/experimenter <topic>` command).
- **Subagents (backend-only):** `explainer` (invoked by `tutor` since 2026-05-27); `latex-verifier`, `citation-verifier` (inline gate + post-hoc hook); `coder` Stage 2 (component surgery and extension regime, invoked by `experimenter`); `critic` extraction-fidelity and extension-fidelity modes (invoked by `experimenter`); `critic` blueprint-check mode (invoked by `implementer`); `evaluator` (Build-evaluate sub-phase, invoked by `experimenter`).
- **Skills (active):** `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-blueprint`, `ml-critique`, `ml-tutor`, `ml-explanation`, `ml-synthesis`, `ml-comparison`, `ml-experiment-design`, `ml-experiment-code` (Stage-1 + Stage-2 sections), `ml-evaluation`.
- **Rules:** `paperlab-config-bootstrap`, `paperlab-regenerate-prompt`, `external-fetch-budget`.
- **Helpers:** `tools/paths.py`, `tools/figures.py` (requires `pymupdf`).
- **Papers:** `Memento` (legacy, in repo), `WorldModel`, `VAE`, `GIB-DS`, `GIB`, `GraphVarBound`, `Dreamer`, `MIbound` (new layout, vault + repo).
