# PaperLab Roadmap

Status as of 2026-05-29. Living document — items move between sections as their status changes.

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
    ├── critic_reviews.md
    ├── tutor_log.md               tutor: per-turn breadcrumb log (append-only)
    ├── tutor_notes.md             tutor: curated study notes (user-triggered)
    ├── <concept>.md               tutor-written (final, user-facing)
    ├── <concept>-<slug>.md        explainer-written (backend intermediate)
    ├── synth__<a>__<b>.md         tutor-written (final, user-facing)
    ├── synth__<a>__<b>-<slug>.md  explainer-written (backend intermediate)
    └── notes.md                   user notes
```

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
| `implementer` | Shipped (+ blueprint mode 2026-06-03) | `ml-code-map` (+ `DEEP_DIVE`), `ml-blueprint` | Map paper concepts to cloned upstream code; write `code_map.md` or deep-dive `code_map__<slug>__<component>.md`. **Blueprint mode** (explicit, opt-in): when no official code exists, reconstruct a framework-agnostic implementation contract `code_blueprint.md` (`status: blueprinted`) from the paper's math, gated pre-emission by the `critic` (draft as payload → retry ×2 → escalate; write on PASS). The hop-1 artifact the `coder` later turns into runnable code. | User: "map / annotate / explain code for `<slug>`"; "blueprint / reconstruct `<slug>`" |
| `critic` | Shipped (+ blueprint-check 2026-06-03) | `ml-critique` | Audit claims, reproducibility, paper↔code alignment; write `critic_reviews.md`. **Blueprint-check mode** (backend, invoked by `implementer`): audits a draft `code_blueprint.md` pre-emission against the critic's own independent reading of the paper's math; returns PASS/FAIL (FAIL on contradiction / inconsistent step; missing invariant warns), writes no file. The firewalled hop-1 guard. | User: "audit / critique / review `<slug>`" (audit); (backend) invoked by `implementer` (blueprint-check) |
| `tutor` | **Shipped (2026-05-27)** | `ml-tutor` (+ `ml-explanation`, `ml-synthesis` when writing concept / synthesis files) | User-facing conversational tutor. Anchored to one paper at a time; paper-grounded + field-grounded; persistent memory via `tutor_log.md`. Invokes `explainer` in the background when paper-bound content is missing. Writes `tutor_log.md` (every turn), and on explicit user request `tutor_notes.md`, `<concept>.md`, `synth__<a>__<b>.md`. | User: `/tutor <slug>` or `/tutor` to resume the most recent session |
| `explainer` | **Backend-only (2026-05-27)** | `ml-explanation`, `ml-synthesis` | Invoked by `tutor`, not by the user. Writes paper-bound intermediates `<concept>-<slug>.md` and `synth__<a>__<b>-<slug>.md` for the tutor to consume. | (Internal — invoked by `tutor`) |
| `visualizer` | **On hold (2026-05-27)** | (archived) | Concept-picture generator. Four implementation iterations did not reach the hand-drawn quality bar. Code, skills, dictionary, and renderers archived on branch `visualizer` and tag `archive-visualizer-2026-05-27`; removed from `main`. See `visualizer-todo.md` for the full chronicle and a research-flavored side-project spec. | (On hold — do not invoke) |
| `figure-verifier` | **On hold (2026-05-27)** | (never authored) | Three-layer pass/fail check on `(concept_text, picture_spec, rendered_png)`. Coupled to the visualizer's retry loop; on hold for the same reason. | (On hold — do not invoke) |
| `prerequisite` | Planned | `ml-prerequisites` (planned) | Scan `spec.md`; detect assumed background; cross-check vault coverage; produce prereq graph + on-demand primers (delegates to `tutor`) | User: "what do I need to know first / check prereqs for `<slug>`" |
| `experimenter` | **Design-phase shell shipped (2026-06-02)** | `ml-experiment-design` | User-facing **orchestrator** for multi-paper empirical comparisons. Holds the interactive session; owns experiment + data-synthesis *design*; does small in-session code tweaks; discusses results. Invokes `comparator` / `coder` / `evaluator`. Notes → `<vault>/experiments/<topic>/`; code/data → `sandbox/experiments/<topic>/`. **Shipped scope:** design phase only (design ⇄ user, trade-offs via `comparator`, optional critic advisory, writes `design.md` with inline gate). Stops at the implement boundary until `coder` / `evaluator` ship. | User: `/experimenter <topic>` |
| `comparator` | **Shipped (2026-05-29)** | `ml-comparison` | **Conceptual** cross-method comparison from `spec.md` (+ `code_map.md` / PDF when needed) along a user-chosen axis; may refine a vague axis via propose-and-confirm. **Dual-mode:** standalone (user) or design-phase input (invoked by `experimenter`). Writes `comparison.md` under `<vault>/experiments/<topic>/`, verified by an inline LaTeX + citation gate. Carries the critic's `[A]`/`[B]` inference discipline. | User: "compare methods for `<topic>`" or (backend) invoked by `experimenter` |
| `coder` | Designed (2026-05-29; blueprint bridge 2026-06-03) | `ml-experiment-code` (planned) | **Backend-only.** One-shot heavy scaffold: writes data-synthesis + method code into `sandbox/experiments/<topic>/` and runs experiments. User-check gate sits between write and run. **Two source modes** (designed 2026-06-03): official code → import in place from `upstream/` and wrap to the harness interface; no code → read `code_blueprint.md` and **generate + assert** (emit the blueprint's invariants as runtime checks, run on synthetic input before done = hop-2 guard). | (Internal — invoked by `experimenter`) |
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

### 1. `tools.tikz` — pre-render TikZ to portable SVG

- **What:** new helper (likely `tools/tikz.py`, or an extension of `tools/figures.py`) that takes a TikZ source string, compiles it to SVG via a TeX engine, caches by content hash under `papers/<slug>/.cache/tikz/<hash>.svg`, and exposes `extract_tikz_to_vault(slug, source)` returning a vault-relative path (mirroring `extract_figure_to_vault`). The visualizer, when the waterfall picks TikZ, embeds `![](figures/diagramN.svg)` instead of a raw ```` ```tikz ```` fence.
- **Why:** SVG renders everywhere — Obsidian (any renderer), Marp preview, marp-cli PPTX / PDF / HTML, GitHub markdown preview, browsers. Raw `tikz` fences only render in Obsidian Reading view with marp-tikz-plus (see Known limitations).
- **Open design question:** where the TeX engine comes from. Either vendor the marp-tikz-plus WASM bundle (portable, ~6 MB in repo) called via a Node bridge, or require a local `tectonic` / `pdflatex` + `dvisvgm` install (simpler code, heavier user setup). Decide when work starts.
- **Acceptance:** the existing VAE concept deck re-emits with SVG embeds and renders correctly in (a) Obsidian Reading view without marp-tikz-plus enabled, (b) `marp-cli` HTML export, (c) PPTX export. The "TikZ only renders in Obsidian Reading view" Known-limitations entry can be deleted once shipped.
- **Why subagent / skill / tool?** Pure deterministic transformation — `tool` per the decision framework, not a subagent.
- **Coupling to visualizer pivot:** previously a blocker if TikZ became the v2 backend. With the visualizer on hold (2026-05-27, see `visualizer-todo.md`), this coupling is dormant. The original slide-deck portability motivation also dissolves with slide decks themselves — re-evaluate whether the unit is still needed before scheduling work.

### 2. `prerequisite` subagent + `ml-prerequisites` skill

- **What:** scans `spec.md`, identifies assumed background concepts, cross-references existing `<vault_paperlab_path>/*/` and the curated `obsidian_vault_root` for coverage, produces a prerequisite graph + on-demand primers for gaps.
- **Interaction model:** detect → check → ask. Presents the unknown list as a checklist; the user picks what to learn. Generated primers delegate to `explainer`.
- **Why subagent + skill:** detecting assumed knowledge needs judgment; the prereq-graph schema is reference.

### 3. Experimenter suite — `experimenter` + `comparator` + `coder` + `evaluator`

**Designed 2026-05-29; `comparator` shipped 2026-05-29.** Full decision
log and rationale in
[`log/2026-05-29-experimenter-design.md`](./log/2026-05-29-experimenter-design.md).
Re-scoped from the original single-paper `ml-sandbox` framing into a
**multi-paper, problem-type-oriented, full-lifecycle** comparison suite.
The previously-parked `comparator` is un-parked and folded in here.

- **Four agents:**
  - `experimenter` (user-facing orchestrator, **designed**) — interactive design + data-synthesis decisions; small in-session code tweaks; discusses results. Skill: `ml-experiment-design`.
  - `comparator` (dual-mode, **shipped 2026-05-29**) — conceptual method comparison from specs along a user-chosen axis. Skill: `ml-comparison`. See "Recently completed" for build notes.
  - `coder` (backend, **designed**) — one-shot heavy scaffold of synth + method code, runs experiments. Skill: `ml-experiment-code`. **Two source modes** (designed 2026-06-03, [`log/2026-06-03-implementer-coder-blueprint-design.md`](./log/2026-06-03-implementer-coder-blueprint-design.md)): official code → import in place + wrap to the harness interface; no code → consume the `implementer`'s `code_blueprint.md` and generate code, emitting the blueprint's invariants as runtime assertions (hop-2 guard).
  - `evaluator` (backend, **designed**) — empirical results interpretation. Skill: `ml-evaluation`.
- **Interaction model — Model 3 (hybrid).** Heavy scaffold one-shot via `coder`; tight write→check→tweak loop in-session via `experimenter`. Mirrors the proven tutor/explainer split.
- **The flow:** design (experimenter ⇄ user) → method trade-offs on demand (`comparator`) → implement+run (`coder`, user-check gate between write and run) → evaluate (`evaluator`) → discuss.
- **Interactive data-design phase** (owned by `experimenter`, Seam A): what property is tested (expressivity, sample efficiency, robustness, ...); what data features stress it (size, density, noise, distribution shift); synthetic vs. small real; minimum viable comparison (metrics, baselines, seeds). The `coder` implements this design; it does not decide it.
- **File layout:** notes/design in vault `<vault>/experiments/<topic>/` (`design.md`, `findings.md`, standalone `comparison.md`); code/data in repo `sandbox/experiments/<topic>/` (`synth/`, `methods/`, `run/`, `results/`, git-ignored `data/`). `<topic>` is user-chosen; the `experiments/` namespace avoids collision with `sandbox/<slug>/`.
- **Path helpers shipped this session:** `repo_experiments_dir(topic)` and `vault_experiments_dir(topic)` in `tools/paths.py` (CLI: `exp-sandbox`, `exp-vault`).
- **`.gitignore` carve-out shipped:** `sandbox/experiments/` re-included from the blanket `sandbox/` ignore; only `sandbox/experiments/*/data/` stays ignored (code + seed committed).
- **Parked sub-decision:** a `coder` verifier gate (a future "does it run?" check analogous to the dissector's LaTeX gate) — noted, not built now.
- **Blueprint bridge (designed 2026-06-03, [`log`](./log/2026-06-03-implementer-coder-blueprint-design.md)).** When a paper has no official code, the `implementer`'s blueprint mode writes `code_blueprint.md` (a framework-agnostic contract, gated pre-emission by the `critic`'s blueprint-check); the `coder` consumes it. Two-hop fidelity: hop-1 (math → blueprint) guarded by the firewalled critic; hop-2 (blueprint → code) guarded by invariants-as-assertions. The **harness interface** (the common `fit`/`predict`-style plug all methods conform to) is owned at design time in `design.md`. Implementer blueprint mode + critic blueprint-check **shipped 2026-06-03**; coder's two modes + harness await the `coder` build.
- **Build order:** `comparator` first (dual-mode, reads only durable specs, independently testable) ✅ **done** → `experimenter` shell (design phase) ✅ **done 2026-06-02** → `coder` → `evaluator`.

### 4. External-data access

- **MCP:** reuse `firecrawl` (already configured). Add a thin `arxiv` MCP only if structured metadata becomes a recurring need.
- **Rule:** `external-fetch-budget.mdc` — max ~5 external fetches per concept; prefer arXiv abstract + 1 blog + author page; never crawl whole sites. Threshold to be tuned.

### 5. `tools.reindex` — graph index over the vault

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
- **Bigger leap — two-memory critic loop (design captured 2026-06-02):** generators share a structured-spec working memory; critics hold a *complementary* representation (consequence lists: limits, signs, types/shapes, invariants, Markov/independence, monotonicity) and gate the working memory **pre-emission** (critic checks → retry ×2 → escalate to user; no disk write/rewrite loop). The graph's `derived_from` / `mentions` edges are the substrate a pre-emission critic needs. Larger effort; not scheduled.

## On hold

Units that were started or shipped and are now paused after running into a quality ceiling that further iteration inside PaperLab is unlikely to clear. Distinct from **Parked** (deferred without trying) and **Planned** (designed, not started). Each on-hold entry points at a postmortem document so the work can be resumed (or respun as a side project) without losing context.

### Visualizer + figure-verifier (on hold 2026-05-27)

The `visualizer` and `figure-verifier` subagents are on hold and archived
(branch `visualizer`, tag `archive-visualizer-2026-05-27`; removed from
`main`). The full chronicle — why it stalled, the four iterations, what
was learned, current limitations, and a research-flavored side-project
spec — lives in [`visualizer-todo.md`](./visualizer-todo.md). Do not
re-derive it here.

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

## Schema improvement candidates

Small refinements to existing schemas that aren't urgent but are worth remembering. These tend to surface during use.

- **Reconsider slide-deck structure** — the current schema (title / headline / one-per-component / results / limitations) is generic. Tweak it to track paper content more faithfully: e.g., split "method" into problem-setup vs. solution slides, surface the loss/objective as its own slide when central, and let `spec.md` §6 grouping drive section count rather than a fixed 8–12 budget. May require enriching `spec.md` fields the dissector currently extracts (e.g., explicit "core contribution" vs. "supporting machinery" tags on §6.1 entries).

## Completed work

The roadmap is forward-looking. Completed-work history has moved to
[`log/changelog_history.md`](./log/changelog_history.md); per-session
decision narratives live in the dated logs under `log/`.

## Reference: what's currently working

- **Subagents (user-facing):** `acquirer`, `dissector`, `implementer`, `critic`, `tutor`.
- **Subagents (backend-only):** `explainer` (invoked by `tutor` since 2026-05-27).
- **Subagents (on hold, 2026-05-27):** `visualizer` (archived to branch `visualizer` and tag `archive-visualizer-2026-05-27`; removed from `main` — see `visualizer-todo.md`).
- **Skills (active):** `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-critique`, `ml-tutor`, `ml-explanation`, `ml-synthesis`.
- **Rules:** `paperlab-config-bootstrap`, `paperlab-regenerate-prompt`.
- **Helpers:** `tools/paths.py`, `tools/figures.py` (requires `pymupdf`).
- **Papers:** `Memento` (legacy, in repo), `WorldModel`, `VAE`, `GIB-DS`, `GIB`, `GraphVarBound`, `Dreamer`, `MIbound` (new layout, vault + repo).
