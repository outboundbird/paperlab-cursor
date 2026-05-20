# PaperLab Roadmap

Status as of 2026-05-20 (end of day). Living document — items move between sections as their status changes.

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
    ├── mdp.md
    ├── code_map.md
    ├── critic_reviews.md
    ├── <concept>.md
    ├── synth__<a>__<b>.md
    ├── slides.md                  Marp deck (later: visualizer)
    ├── *.tldr / *.svg / *.png     diagrams (later: visualizer)
    ├── notes.md                   user notes
    └── tutor_log.md               later: tutor
```

Current `vault_paperlab_path` (work machine): `C:/Users/e0482362/OneDrive - Sanofi/Workspace/Topics/public/Modeling 🎓/PaperLab`.

### Cross-references

- `paper-info.md` in the vault contains **absolute** links to the repo-side PDF and upstream code, constructed from `repo_root` in `paperlab.config.yaml`.
- Absolute paths differ per machine. `paperlab.config.yaml` is per-machine and git-ignored. Each machine carries its own copy.

### Unified file convention

- One schema. No agent-only or user-only file variants.
- On regeneration of an existing file, agents MUST ask: **replace**, **append**, or **abort**. See `.cursor/rules/paperlab-regenerate-prompt.mdc`.
- All paper folders follow the same flat structure. No per-paper config files.

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

### 1. `prerequisite` subagent + `ml-prerequisites` skill

- **What:** scans `spec.md`, identifies assumed background concepts, cross-references existing `<vault_paperlab_path>/*/` and the curated `obsidian_vault_root` for coverage, produces a prerequisite graph + on-demand primers for gaps.
- **Interaction model:** detect → check → ask. Presents the unknown list as a checklist; the user picks what to learn. Generated primers delegate to `explainer`.
- **Why subagent + skill:** detecting assumed knowledge needs judgment; the prereq-graph schema is reference.

### 2. `experimenter` subagent + `ml-sandbox` skill

- **What:** scaffolds a minimal toy implementation in `sandbox/<slug>/` with a small synthetic or standard dataset, enabling A/B comparison of methods.
- **Interactive data-design phase:** before generating code, the agent dialogues with the user about:
  - What property of the method is being tested (expressivity, sample efficiency, robustness, ...).
  - What data features would stress that property (size, density, noise, distribution shift, ...).
  - Synthetic vs. small real dataset.
  - Minimum viable comparison (metrics, baselines, seeds).
- **Pairs with:** future `comparator`.

### 3. External-data access

- **MCP:** reuse `firecrawl` (already configured). Add a thin `arxiv` MCP only if structured metadata becomes a recurring need.
- **Rule:** `external-fetch-budget.mdc` — max ~5 external fetches per concept; prefer arXiv abstract + 1 blog + author page; never crawl whole sites. Threshold to be tuned.

## Parked

Designed but deferred until the units above are stable.

### `tutor` subagent + `ml-socratic` skill

- **What:** interactive, multi-turn Socratic teacher. Reads `spec.md` + concept files, picks next concept, explains (delegating to `visualizer`), quizzes, adapts.
- **State:** `tutor_log.md` per paper.
- **Why parked:** log schema and overlap with explainer outputs need more thought.

### `comparator` subagent + `ml-comparison` skill

- **What:** cross-paper synthesis. Inputs N paper slugs + a comparison axis (e.g., "Graph Information Bottleneck objective formulations"). Output: `<vault>/PaperLab/comparisons/<topic>/comparison.md`.
- **Why parked:** synthesis design is tricky; revisit when there are 3+ comparable papers in the vault.

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
- **Possible fix:** make `paper-info.md` use a placeholder like `{repo_root}/papers/<slug>/<slug>.pdf` that an Obsidian plugin or hook resolves at view time. Medium effort, low priority.

### Figure extraction occasionally crops imperfectly

- **What:** for some PDF layouts the caption-block-width heuristic still over- or under-crops (observed on GIB-DS and one inset figure in Memento).
- **Workaround:** add a manual bbox entry in `papers/<slug>/.cache/figures/manual_crops.json`, or use `--whole-page` to render the full page and let the slide layout class handle scaling.
- **Trigger to revisit:** if a paper of interest has more than ~1 unusable crop.

## Schema improvement candidates

Small refinements to existing schemas that aren't urgent but are worth remembering. These tend to surface during use.

- **Reconsider slide-deck structure** — the current schema (title / headline / one-per-component / results / limitations) is generic. Tweak it to track paper content more faithfully: e.g., split "method" into problem-setup vs. solution slides, surface the loss/objective as its own slide when central, and let `spec.md` §6 grouping drive section count rather than a fixed 8–12 budget. May require enriching `spec.md` fields the dissector currently extracts (e.g., explicit "core contribution" vs. "supporting machinery" tags on §6.1 entries).

## Recently completed (2026-05-20)

- **LaTeX-in-charts policy resolved** — layered approach codified in `ml-visualization/SKILL.md`:
  - **Mermaid (default for structural diagrams):** atomic symbols use Unicode (`θ`, `μ`, `Σ`, `ℝ`, `zₜ`, `∇L`); compound expressions go in the right column and labels reference them as `(eq. N)`. Carved out as an exception in `AGENTS.md` to the "no Unicode math" rule — Mermaid labels only.
  - **TikZ via `marp-tikz-plus` (escalation for math-heavy diagrams):** verified end-to-end in Obsidian preview against the [kevinyuan/marp-tikz-plus engine](https://github.com/kevinyuan/marp-tikz-plus). Plate notation, commutative diagrams, expectations with subscripted distributions, `\mathbb` / `\mathcal` / fractions all render natively in node labels. Authoring rules captured: no `\documentclass`, no `\usepackage{tikz}`, allowed `\usepackage` set limited to the engine's supported list (`amsmath`, `amssymb`, `amsfonts`, `array`, `tikz-cd`, `pgfplots`, `circuitikz`, `chemfig`, `tikz-3dplot`), `\usetikzlibrary{...}` must precede `\begin{document}`, `[scale=2]` for Marp slides.
  - **Extract-first waterfall extended** to four priorities: extracted paper figure → TikZ (math-heavy) → Mermaid (structural flow) → drop.
  - **Pre-write check added for TikZ blocks** alongside the existing Mermaid check; the visualizer agent now reports both counts on completion.
  - **KaTeX/MathJax preprocessing rejected** as overkill given that TikZ handles the math-heavy case natively.

## Recently completed (2026-05-19)

- **`visualizer` subagent + `ml-visualization` skill** — produces Marp slide decks (`slides.md`) and per-concept visualizations (`<concept>__viz.md`) from `spec.md` / `code_map.md` / `<concept>.md`.
- **Extract-first waterfall** — visualizer prefers extracted paper figures over generated diagrams; Mermaid/TikZ/matplotlib/tldraw are documented fallbacks.
- **PDF figure extraction (`tools/figures.py`)** —
  - `list_figures` — caption parser; supports `Figure N` / `Table N`, single- and double-column PDFs.
  - `extract_figure` — caption-block-width crop heuristic: text-block complement on both axes, paragraph-shape filter to exclude table rows / figure-internal labels, table-caption-above-or-below fallback, manual-crop escape hatch via `papers/<slug>/.cache/figures/manual_crops.json`.
  - `extract_figure_to_vault` — copies the cached PNG into `<vault>/<slug>/figures/` and returns a **vault-relative** path so embeds work across drives / OneDrive.
  - `captions_by_component` — looks up figures by prose context.
  - CLI: `list`, `extract`, `extract-to-vault`, `by-component`.
- **Semantic figure tagging in `spec.md` §4.5** — dissector classifies each figure as `headline` / `result` / `qualitative` / `thumbnail` via a two-pass keyword + prose cross-check.
- **YAML front-matter `paper: <slug>`** — added to all agent-generated notes and slides for vault-side queries.
- **Slide layout routing by figure aspect ratio + source** — three Marp classes:
  - `split` — square/portrait figure (W/H < 1.4) or Mermaid/TikZ diagrams; two-column figure-left / prose-right.
  - `figure-top` — landscape figure (1.4 ≤ W/H < 2.5); figure spans full width above a short prose strip.
  - `figure-full` — panorama / large tables (W/H ≥ 2.5); figure fills the slide, italic caption only.
  - Mermaid/TikZ stay forced to `split` so they don't blow up the slide; only extracted figures get the wider classes. CSS lives in the external `paperlab.css` Marp theme.
- **Visualizer overwrite contract (no AskQuestion privilege)** — when `slides.md` / `<concept>__viz.md` already exists, visualizer emits a text prompt with path / size / mtime and asks **replace / append / abort?**, then ends the turn until the user replies.

### Validation runs

- **`WorldModel`**, **`VAE`** — visualizer end-to-end: content generation OK, vault-relative figure embeds OK, overwrite prompt OK.
- **`Memento`**, **`GIB-DS`** — figure extraction spot-checked; most figures and tables crop cleanly. A few imperfect crops remain (see Known limitations).

## Recently completed (2026-05-18)

- **File layout contract** — repo holds source material (`papers/<slug>/<slug>.pdf`, `supplementals/`, `upstream/<slug>/`); vault holds all agent-generated markdown flat under `<vault>/<slug>/`.
- **Per-machine config** — `paperlab.config.yaml` (git-ignored) + `paperlab.config.example.yaml` (committed). Keys: `repo_root`, `vault_paperlab_path`, `obsidian_vault_root`.
- **Path-resolution helper** — `tools/paths.py` exposes `vault_path`, `vault_slug_dir`, `repo_pdf_path`, `repo_paper_dir`, `repo_supplementals_dir`, `repo_upstream_dir`, `repo_sandbox_dir`, plus a `python -m tools.paths` CLI. UTF-8 stdout enforced (vault path contains 🎓).
- **Always-on rules:**
  - `paperlab-config-bootstrap.mdc` — every agent resolves paths through `tools/paths.py`; documents read/write conventions; defines slug rule (verbatim user input).
  - `paperlab-regenerate-prompt.mdc` — never silently overwrite existing files in the vault; ask **replace / append / abort**.
- **Sweep of all 5 agents + 6 skills** — every `papers/<slug>/...` write target replaced with `vault_path(...)`; source-material reads now go through `repo_*` helpers.
- **Acquirer** — now creates both repo folder and vault folder; writes `paper-info.md` to the vault with absolute links to repo-side material.
- **Dependencies** — `requirements.txt` with `PyYAML>=6.0`.
- **Bug fix** — slug-mangling: agents were lowercasing/hyphenating user-provided slugs. Bootstrap rule and acquirer agent now both enforce verbatim slug.

### Validation runs

- **`WorldModel`** (acquired from scratch end-to-end): acquirer, dissector, implementer all produced files in the correct repo/vault locations. Critic and explainer not yet exercised.
- **`Memento`** (pre-migration, in repo): left untouched per agreed plan; remains at `papers/Memento/`.

## Reference: what's currently working

- **Subagents:** `acquirer`, `dissector`, `implementer`, `explainer`, `critic`, `visualizer`.
- **Skills:** `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-explanation`, `ml-synthesis`, `ml-critique`, `ml-visualization`.
- **Rules:** `paperlab-config-bootstrap`, `paperlab-regenerate-prompt`.
- **Helpers:** `tools/paths.py`, `tools/figures.py` (requires `pymupdf`).
- **External Marp theme:** `marp_theme_path` in `paperlab.config.yaml` → `paperlab.css` (defines `split` / `figure-top` / `figure-full`).
- **Papers:** `Memento` (legacy, in repo), `WorldModel`, `VAE`, `GIB-DS` (new layout, vault + repo).
