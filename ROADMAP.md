# PaperLab Roadmap

Status as of 2026-05-18 (end of day). Living document — items move between sections as their status changes.

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

### 1. `visualizer` subagent + `ml-visualization` skill — **next**

- **What:** turns `spec.md`, `<concept>.md`, and `code_map.md` into visual artifacts — diagrams, flowcharts, slide decks — to support visual learning.
- **Primary outputs:** Mermaid diagrams (inline in markdown) and Marp slide decks (`<slug>/slides.md`). Both render natively in Obsidian (Marp Slides plugin) and GitHub.
- **Fallback outputs when Mermaid/Marp are inadequate:**
  - matplotlib / PIL figures saved as PNG/SVG for numerical plots or precise geometry.
  - TikZ for publication-quality math diagrams.
  - tldraw canvases (`.tldr` files written directly into the vault, opens natively in Obsidian's tldraw plugin) for architectural sketches.
- **Why subagent + skill:** choosing *what* to visualize needs judgment (subagent); diagram conventions and format-selection rules are reusable reference (skill).
- **First test case:** `WorldModel` (already acquired + dissected + mapped).
- **Acceptance:** produces at least one Mermaid diagram + a Marp deck with diagrams (not just rephrased bullets).

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

## Schema improvement candidates

Small refinements to existing schemas that aren't urgent but are worth remembering. These tend to surface during use.

- _(none yet — fill in as we use the system)_

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

- **Subagents:** `acquirer`, `dissector`, `implementer`, `explainer`, `critic` (last two functional but not yet exercised end-to-end under the new layout).
- **Skills:** `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-explanation`, `ml-synthesis`, `ml-critique`.
- **Rules:** `paperlab-config-bootstrap`, `paperlab-regenerate-prompt`.
- **Helpers:** `tools/paths.py`.
- **Papers:** `Memento` (legacy, in repo), `WorldModel` (new layout, vault + repo).
