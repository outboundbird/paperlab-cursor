# PaperLab Roadmap

Status as of 2026-05-27. Living document — items move between sections as their status changes.

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
| `dissector` | Shipped | `ml-paper-spec` | Read `<slug>.pdf`; write `spec.md` (structured extraction). (Planned auto-invocation of `visualizer` on §6 pseudocode blocks suspended while `visualizer` is on hold.) | User: "dissect / parse / summarize / spec paper `<slug>`" |
| `implementer` | Shipped | `ml-code-map` (+ `DEEP_DIVE`) | Map paper concepts to cloned upstream code; write `code_map.md` or deep-dive `code_map__<slug>__<component>.md` | User: "map / annotate / explain code for `<slug>`" |
| `explainer` | Shipped | `ml-explanation`, `ml-synthesis` | Per-concept math explanations (`<concept>.md`) and multi-concept syntheses (`synth__<a>__<b>.md`) | User: "explain `<concept>` / synthesize `<a>` and `<b>` from `<slug>`" |
| `critic` | Shipped | `ml-critique` | Audit claims, reproducibility, paper↔code alignment; write `critic_reviews.md` | User: "audit / critique / review `<slug>`" |
| `visualizer` | **On hold (2026-05-27)** | `ml-visualization`, `ml-visualization-dsl` | Concept-picture generator. Four implementation iterations (graphviz baseline → cast/headline schema → DSL with `Juxtapose`/`Decompose` → end-to-end DSL run on real concepts) did not reach the hand-drawn quality bar. Spec, skills, renderers, and dictionary retained as reusable artifacts. See `visualizer-todo.md` for the full chronicle and a research-flavored side-project spec. | (On hold — do not invoke) |
| `figure-verifier` | **On hold (2026-05-27)** | `ml-figure-verify` (never authored) | Three-layer pass/fail check on `(concept_text, picture_spec, rendered_png)`. Coupled to the visualizer's retry loop; on hold for the same reason. | (On hold — do not invoke) |
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
- **Coupling to visualizer pivot:** previously a blocker if TikZ became the v2 backend. With the visualizer on hold (2026-05-27, see `visualizer-todo.md`), this coupling is dormant. The original slide-deck portability motivation also dissolves with slide decks themselves — re-evaluate whether the unit is still needed before scheduling work.

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

## On hold

Units that were started or shipped and are now paused after running into a quality ceiling that further iteration inside PaperLab is unlikely to clear. Distinct from **Parked** (deferred without trying) and **Planned** (designed, not started). Each on-hold entry points at a postmortem document so the work can be resumed (or respun as a side project) without losing context.

### Visualizer + figure-verifier (on hold 2026-05-27)

- **What:** the `visualizer` subagent (Marp slide decks v1, concept-picture generator v2) and the planned `figure-verifier` subagent.
- **Why on hold:** four implementation iterations (graphviz baseline → cast/headline schema → DSL with `Juxtapose`/`Decompose` → end-to-end DSL run on real concepts) did not reach the hand-drawn quality bar the user is targeting. Run-1 of the DSL on GIB Markov representation produced an algebraically-correct picture that did not visually resemble a Markov chain; Run-3 on GIB-Cat sampling correctly refused to force-fit the DSL but the graphviz fallback still emitted spreadsheet-style labels. The architectural ceiling is the LLM's inability to make global spatial decisions; closing that gap is a research problem (corpus + learned layout model), not a tooling problem.
- **Artifacts retained as reusable inputs:** `tools/visualize_concept.py` (graphviz pipeline), `tools/figure_dsl.py` + `tools/render_dsl.py` (operator-tree DSL skeleton), `.cursor/skills/ml-visualization/` + `ml-visualization-dsl/`, `DICTIONARY.md` / `.pdf` / `symbols/` (~70 typed visual idioms), sandbox stress-test PNGs, `.cursor/agents/visualizer.md`.
- **Pointer:** see [`visualizer-todo.md`](./visualizer-todo.md) at the repo root for the full chronicle of what was tried, what was learned, and a research-flavored side-project spec (corpus, model directions, evaluation, baselines, suggested first milestone).
- **Trigger to revisit:** (a) a side-project run produces a layout policy that beats the iteration-3 DSL on a labeled corpus; or (b) PaperLab's needs shift to figure quality being a blocker rather than a nice-to-have.

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

### (Resolved 2026-05-22) Visualizer redesign: concept-picture generator (v2)

Schema and backend decision **resolved**; implementation pending. Moved from "Parked decisions" to "Recently completed (2026-05-22)" with the resolved facts. Original framing preserved below for traceability; see "Recently completed" for the resolution.

Original framing (2026-05-20):

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

### Visualizer reference card — open follow-ups

Tracking the loose ends from the 2026-05-22 dictionary-PDF work. None are blockers for visualizer v2 implementation; they're quality-of-life items for the reference card.

- **Close the 36 placeholder rows in `DICTIONARY.pdf`** — half of the dictionary still shows `— no tile —` in the Symbol column. Each gap is one `_render_<id>` function in `tools/build_symbol_sheet.py` plus an entry in the `RENDERERS` dict. The PDF surfaces the gap on every rebuild, which makes this a fill-in-as-you-go task rather than a single push. Priority order: actions with no tile (used most often in the validation runs), then entities, then relations.
- **Make tile regeneration incremental** — `tools.build_symbol_sheet.main()` currently re-renders every tile on every PDF rebuild (~75 s on Windows). Add content-hash-based skip (hash the renderer source + `PREAMBLE` + dictionary row → PNG mtime check). Would drop the pre-commit hook's overhead from ~75 s to ~3 s for typical edits that don't touch the tile registry.
- **CI verification of dictionary-PDF freshness** — the pre-commit hook is opt-in (`git config core.hooksPath tools/hooks`). Add a lightweight CI check that runs `python -m tools.build_dictionary_pdf` and diffs against the committed `DICTIONARY.pdf`, failing if they differ. Catches contributors who skipped the hook setup. Open question: PDF bytes aren't reproducible across ReportLab versions / platforms, so the diff may need to be on extracted text only.
- **Expose the PDF builder via `tools.build` umbrella** — once both `build_symbol_sheet` and `build_dictionary_pdf` exist, plus the planned `tools.tikz` and any future builders, the right shape is one `python -m tools.build [target]` entry point with `dictionary`, `tiles`, `tikz`, `all` targets. Defers until at least three builders coexist.
- **Render math beyond the Unicode subset** — the LaTeX expander in `build_dictionary_pdf.py` covers ~60 commands found in `DICTIONARY.md` today. New dictionary entries with unsupported commands (`\mathfrak`, `\overline`, `\sqrt`, fractions) will render the command name literally. Extend the map as gaps appear; if the long tail grows past ~30 unsupported commands, switch the PDF math strategy to embed math as inline PNGs rendered by matplotlib's mathtext.
- **Dictionary entry IDs aren't currently citable from prose** — when the visualizer agent (or any chat) wants to reference an entry by ID (e.g., "uses A7 aggregate"), there's no quick lookup from ID → row. The PDF helps but isn't searchable from the agent's context. Possible fix: a `tools.dict_lookup` CLI (`python -m tools.dict_lookup A7` → prints the canonical name + symbolic representation). Cheap, deferred until an agent actually needs it.

## Recently completed (2026-05-22)

- **Dictionary PDF reference card + sync hook** — replaces the previous `symbols/atlas.png` quick-glance grid with a real reference document.
  - `tools/build_dictionary_pdf.py` parses the three category tables in `DICTIONARY.md`, augments each row with a fifth **Symbol** column embedding the matching tile from `symbols/<id>.png`, and emits `.cursor/skills/ml-visualization/DICTIONARY.pdf` via ReportLab (no LaTeX / pandoc / Chromium needed). Landscape A4, repeating table headers, alternating row backgrounds. Run as `python -m tools.build_dictionary_pdf` (full rebuild) or `... --skip-tiles` (PDF only, ~3 s).
  - Sync semantics are list-level: every row in `DICTIONARY.md` appears in the PDF, but entries without a registered renderer in `build_symbol_sheet.RENDERERS` get a visible `— no tile —` placeholder, so drift between dictionary and tiles is reported inside the PDF itself. Current state: 72 rows total, 36 with tiles, 36 placeholders.
  - Small LaTeX→Unicode expander in the PDF builder so `$\sim$`, `$\theta$`, `$\rho$`, `$\mathbb{E}$`, etc. render legibly instead of leaking command names.
  - `tools/hooks/pre-commit` + `tools/hooks/README.md` — source-controlled git hook installed once per clone with `git config core.hooksPath tools/hooks`. When `DICTIONARY.md` is staged, the hook rebuilds the PDF and tiles, re-stages them, and aborts the commit on build failure. `git commit --no-verify` skips it for WIP.
  - `tools/build_symbol_sheet.py` lost its `_build_atlas()` step and `atlas.png` / `atlas.dot` are deleted. The PDF is now the canonical visual reference card.
- **Visualizer v2 schema + backend decision** — the v2 concept-picture generator's schema is locked in. Three resolved questions:
  - **Source of visual vocabulary:** `.cursor/skills/ml-visualization/DICTIONARY.md` (v0.1). 23 entities, 12 relations, 37 actions, each row carries canonical name + aliases + symbolic representation. Verb-only canonical action names; math-symbol convention for `≤ ≥ = ≈ Σ ∫`; three-step gap rule (compose → closest-with-label → text-arrow fallback `— [verb objective] →` → stop and report) so the visualizer never invents new symbols silently; atomicity rule (one action = one arrow).
  - **Rendering backend:** **graphviz**. Picked after a head-to-head on the same panel via matplotlib (manual layout, ~5 visible collisions), tldraw (auto-routing OK but no headless export from the current MCP), and graphviz (auto-layout + direct PNG/SVG, no Chrome/Node dependency). Graphviz wins for the scripted, automated path. Portable Windows binary installed at `tools/graphviz/Graphviz-14.1.5-win64/` (git-ignored except for README), Linux install via `apt install graphviz`. Resolver in `tools.paths.graphviz_dot()` returns the per-machine binary path.
  - **Validation:** dictionary stress-tested on three concepts as text-spec inventories (GraphVarBound §6.1 TRW-IS, GIB §3.1 Markov representation, Dreamer §6.2 latent imagination AC). All three rendered with ≤ 1 text-arrow fallback and ≤ 1 composition each; zero invented idioms. GIB Panel B (per-layer relay cell) rendered end-to-end on all three backends; graphviz output (`sandbox/GIB/dry-run-dict-panel-b-graphviz.png`) is the reference.
- **Symbol-sheet atlas** — `.cursor/skills/ml-visualization/symbols/` now contains one PNG + SVG tile per dictionary entry (35 of 72 entries covered for v0.1 — the high-traffic ones from the three validation runs) plus a composite `atlas.png`. Generated by `python -m tools.build_symbol_sheet`, which parses `DICTIONARY.md` for the entry IDs, hand-renders each tile via graphviz, and warns about (a) dictionary entries with no renderer and (b) registered renderers with no dictionary entry — so the two stay in list-level sync.
- **`tools.paths.graphviz_dot()`** — resolver added. Tries `tools/graphviz/Graphviz-*/bin/dot[.exe]` first (portable, per-machine, git-ignored), then falls back to system `dot` on PATH. CLI surface: `python -m tools.paths dot`. Lets the same scripts work on the Windows-no-admin laptop and the Linux-admin desktop without code changes.
- **SKILL.md wired to DICTIONARY.md** — `ml-visualization/SKILL.md` now defines the concept-picture workflow (text → thesis → dictionary inventory → gap rule → atomicity rule → picture spec → graphviz render → verify against thesis) and routes the concept-picture mode to graphviz in the format-selection table. The dictionary, the atlas, and the atomicity rule all have prose pointers from the skill.

### Validation runs (2026-05-22)

- **Three concept inventories** completed as text specs against the dictionary (GraphVarBound §6.1, GIB §3.1, Dreamer §6.2). Same shape across three paper styles: 19-24 direct dictionary hits, ≤ 1 composition, ≤ 1 text-arrow fallback, 0 invented idioms. Detailed inventories captured in chat transcript.
- **One concept rendered through three backends.** GIB Panel B (per-layer relay cell) under matplotlib (`sandbox/GIB/dry-run-dict-panel-b-relay-cell.png`), tldraw (canvas `byw8g492` on the tldraw cloud), and graphviz (`sandbox/GIB/dry-run-dict-panel-b-graphviz.png`). Zero dictionary entries failed to draw on any backend; all readability differences were backend-level (layout, fonts, dashed envelopes).

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

- **Subagents (active):** `acquirer`, `dissector`, `implementer`, `explainer`, `critic`.
- **Subagents (on hold, 2026-05-27):** `visualizer` (artifacts retained — see `visualizer-todo.md`).
- **Skills (active):** `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-explanation`, `ml-synthesis`, `ml-critique`.
- **Skills (retained but unused while visualizer is on hold):** `ml-visualization` (+ `DICTIONARY.md` + `DICTIONARY.pdf` + `symbols/`), `ml-visualization-dsl`.
- **Rules:** `paperlab-config-bootstrap`, `paperlab-regenerate-prompt`.
- **Helpers:** `tools/paths.py` (now exposing `graphviz_dot()`), `tools/figures.py` (requires `pymupdf`), `tools/build_symbol_sheet.py`, `tools/build_dictionary_pdf.py` (requires `reportlab`).
- **Git hooks:** source-controlled under `tools/hooks/` (install once with `git config core.hooksPath tools/hooks`). `pre-commit` keeps `DICTIONARY.pdf` and `symbols/` in sync with `DICTIONARY.md`.
- **External Marp theme:** `marp_theme_path` in `paperlab.config.yaml` → `paperlab.css` (defines `split` / `figure-top` / `figure-full`).
- **External binaries:** graphviz `dot` resolved per-machine (`tools/graphviz/` portable on Windows-no-admin; system install on Linux/macOS).
- **Papers:** `Memento` (legacy, in repo), `WorldModel`, `VAE`, `GIB-DS`, `GIB`, `GraphVarBound`, `Dreamer`, `MIbound` (new layout, vault + repo).
