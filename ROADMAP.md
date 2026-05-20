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

## Agents

Living table of all subagents in the project. Update whenever an agent ships, is parked, or changes role.

| Agent | Status | Skill(s) | Role | Invocation cue |
|---|---|---|---|---|
| `acquirer` | Shipped | `ml-acquisition` | Set up per-paper repo + vault folders; download PDF / supplements; clone upstream; write `paper-info.md` | User: "acquire / add / initialize / download paper `<slug>`" |
| `dissector` | Shipped | `ml-paper-spec` | Read `<slug>.pdf`; write `spec.md` (structured extraction). Auto-invokes `visualizer` for each pseudocode block in §6 (planned, see visualizer entry). | User: "dissect / parse / summarize / spec paper `<slug>`" |
| `implementer` | Shipped | `ml-code-map` (+ `DEEP_DIVE`) | Map paper concepts to cloned upstream code; write `code_map.md` or deep-dive `code_map__<slug>__<component>.md` | User: "map / annotate / explain code for `<slug>`" |
| `explainer` | Shipped | `ml-explanation`, `ml-synthesis` | Per-concept math explanations (`<concept>.md`) and multi-concept syntheses (`synth__<a>__<b>.md`) | User: "explain `<concept>` / synthesize `<a>` and `<b>` from `<slug>`" |
| `critic` | Shipped | `ml-critique` | Audit claims, reproducibility, paper↔code alignment; write `critic_reviews.md` | User: "audit / critique / review `<slug>`" |
| `visualizer` | Shipped (v1) — pivot in progress | `ml-visualization` | **v1 (current):** Marp slide decks + per-concept viz markdown. **v2 (planned, see Parked decisions):** concept-picture generator only — one PNG per concept to `<vault>/<slug>/figures/`. | v1: "make slides / visualize `<slug>`". v2: "draw / visualize `<concept>` from `<slug>`" + auto from `dissector` on pseudocode |
| `prerequisite` | Planned | `ml-prerequisites` (planned) | Scan `spec.md`; detect assumed background; cross-check vault coverage; produce prereq graph + on-demand primers (delegates to `explainer`) | User: "what do I need to know first / check prereqs for `<slug>`" |
| `experimenter` | Planned | `ml-sandbox` (planned) | Scaffold toy implementation in `sandbox/<slug>/`; interactive data-design phase; pairs with future `comparator` | User: "build a toy / sandbox / experiment for `<slug>`" |
| `tutor` | Parked | `ml-socratic` (parked) | Interactive multi-turn Socratic teacher; reads `spec.md` + concept files; state in `tutor_log.md` | (Parked) |
| `comparator` | Parked | `ml-comparison` (parked) | Cross-paper synthesis on a comparison axis; output to `<vault>/PaperLab/comparisons/<topic>/comparison.md` | (Parked) |

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
- **Coupling to visualizer pivot:** if TikZ is selected as a v2 backend (see Parked decisions → "Visualizer redesign"), this unit becomes a blocker. If not, the original slide-deck portability motivation dissolves with slide decks themselves — re-evaluate whether the unit is still needed.

### 2. `prerequisite` subagent + `ml-prerequisites` skill

- **What:** scans `spec.md`, identifies assumed background concepts, cross-references existing `<vault_paperlab_path>/*/` and the curated `obsidian_vault_root` for coverage, produces a prerequisite graph + on-demand primers for gaps.
- **Interaction model:** detect → check → ask. Presents the unknown list as a checklist; the user picks what to learn. Generated primers delegate to `explainer`.
- **Why subagent + skill:** detecting assumed knowledge needs judgment; the prereq-graph schema is reference.

### 3. `experimenter` subagent + `ml-sandbox` skill

- **What:** scaffolds a minimal toy implementation in `sandbox/<slug>/` with a small synthetic or standard dataset, enabling A/B comparison of methods.
- **Interactive data-design phase:** before generating code, the agent dialogues with the user about:
  - What property of the method is being tested (expressivity, sample efficiency, robustness, ...).
  - What data features would stress that property (size, density, noise, distribution shift, ...).
  - Synthetic vs. small real dataset.
  - Minimum viable comparison (metrics, baselines, seeds).
- **Pairs with:** future `comparator`.

### 4. External-data access

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

### TikZ only renders in Obsidian Reading view

- **What:** ```` ```tikz ```` fenced blocks emitted by the visualizer render in Obsidian's Reading view (via the `marp-tikz-plus` plugin's TikZ markdown post-processor), but **not** in Marp slide preview (Obsidian's Marp Slides plugin or VS Code Marp), nor in `marp-cli` HTML/PDF/PPTX export. In those targets the raw `\begin{tikzpicture}` source appears verbatim as a code block in the slide.
- **Why:** marp-tikz-plus's PPTX/PDF export commands DO pre-render TikZ to SVG before calling marp-cli, but this only works when export is launched from the plugin's command palette in Obsidian — not from other Marp tools.
- **Workaround:** preview decks in Obsidian Reading view; export PPTX/PDF from the marp-tikz-plus command palette in Obsidian. Avoid VS Code Marp and standalone `marp-cli` until Option 3 (`tools.tikz`) lands.
- **Possible fix:** the planned `tools.tikz` unit (see Planned units) pre-renders every TikZ block to SVG at write time, so the visualizer embeds portable `![](figures/diagramN.svg)` instead of raw `tikz` fences. SVG renders in every downstream tool.

## Parked decisions

Open design questions deliberately deferred pending more evidence. Capture enough context here that picking the thread back up is cheap.

### Visualizer redesign: concept-picture generator (v2)

Pivot decided 2026-05-20. v1 (slide decks + per-concept viz markdown) is being replaced by a concept-picture-only agent. Captured here in detail so tomorrow's continuation has everything it needs.

#### v1 pain points motivating the pivot

- Slide decks don't pick up key content from `spec.md` faithfully; section structure is too generic.
- Slide content orchestration is weak — logic flow across slides drifts off-topic.
- Generated diagrams are too simple or miss the gist of the concept.
- Extract-first waterfall pulled in PDF figures that the dissector already tracks in `spec.md` §4.5 — duplicated responsibility.

#### v2 contract

**Mission:** turn a textual concept into a single high-quality picture that *embodies* the concept's structure. Framed as "representation learning": encode concept text → latent structural representation → decode to a 2D picture whose visual elements correspond to the nouns/objects in the text.

**Inputs:** one of
- `<vault>/<slug>/<concept>.md` (written by `explainer`).
- A pseudocode block or specific passage from `<vault>/<slug>/spec.md`.

**Output:** one PNG per invocation, written to `<vault>/<slug>/figures/<concept>.png`. No slide deck. No `<concept>__viz.md` wrapper. The `<concept>.md` (or relevant section in `spec.md`) embeds the image directly via `![](figures/<concept>.png)`.

**Picture-kind routing (initial taxonomy):**

| Concept kind | Picture |
|---|---|
| Procedural / pseudocode | Flowchart (boxes + directed edges) |
| Probability distribution (Gaussian, mixture, posterior, ...) | Density / bell curve plot |
| Stochastic process (Markov chain, HMM, ...) | Chain of nodes with transition arrows |
| Message passing / GNN | Small graph with annotated edge updates |
| Linear algebra object (matrix, tensor, vector) | Drawn grid with shape and dims labeled |
| Geometric / manifold | Coordinate frame with the object drawn in it |
| Optimization landscape | Contour or surface with a trajectory |

Taxonomy extends as new picture kinds surface in real papers.

**Invocation:**

- **Manual:** user asks for a picture of a specific concept by name; agent locates the matching `<concept>.md` (or `spec.md` passage) and renders.
- **Automatic — committed:** `dissector` triggers `visualizer` once per pseudocode block found in `spec.md` §6, producing a procedural flowchart alongside the pseudocode.
- **Automatic — deferred:** `explainer` auto-trigger at end of each `<concept>.md` (decision postponed).

#### Open: rendering backend

Backend choice deliberately not fixed. Feasibility check on current Windows machine (2026-05-20):

- ✅ Available: Python 3.12, matplotlib 3.10, numpy 2.3, Pillow 11.2, networkx 3.5.
- ❌ Missing: Graphviz (`dot`), Node.js + npm (so no mermaid-cli, no D2, no vega-cli), Tectonic / pdflatex, Java.
- Note: `node.exe` on PATH is Cursor-internal, not a usable Node install.

**Live backend options** (combinable into a hybrid picture-kind router):

1. **matplotlib + networkx** — zero install; works today; flowcharts and graphs look plain.
2. **+ Graphviz** — small install; biggest visible quality jump per MB; unlocks clean auto-layouts for chains, flowcharts, message passing.
3. **+ Tectonic (TikZ)** — unlocks math-heavy diagrams (commutative diagrams, plate notation); couples to Planned unit #1 `tools.tikz`.
4. **+ Node.js + mermaid-cli** — unlocks Mermaid → PNG and other npm-distributed tools.
5. **Other candidates surveyed but not yet weighed:** seaborn, plotly (`kaleido`), altair / vega-lite (`vl-convert`), PIL primitives, schemdraw, D2, PlantUML, manim, Asymptote, Playwright + HTML/SVG.
6. **Ruled out:** AI image generation (DALL·E / Stable Diffusion / Midjourney) — fails on "picture must faithfully embody the concept's structure".

**Trigger to revisit:** 2026-05-21. Project will also run on a Linux machine where installs are unrestricted; backend decision must account for both environments. Decide after sketching one concept end-to-end (suggested candidates: VAE encoder/decoder, a Gaussian, a Markov chain) under the top-2 backend options.

#### Migration shape (open)

Not yet decided: rip-and-replace v1 in one PR, build v2 alongside, or skill-first design-doc-then-implement.

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
- **Visualizer pivot decided** — v1 (slide decks + viz markdown) will be replaced by v2, a concept-picture generator writing PNGs to `<vault>/<slug>/figures/`. Reference framework captured in Parked decisions → "Visualizer redesign". Backend selection deferred pending tomorrow's continuation and Linux-machine feasibility.
- **Agents table added** to the top of the roadmap as a single source of truth for agent status, role, and invocation cues. To be kept up to date as agents ship / change role / park.

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
