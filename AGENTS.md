# PaperLab: Agent-Assisted Reading Of ML Methods Papers

PaperLab helps the user understand mathematics in machine learning and deep learning papers.

## Project Conventions

- Python code uses type hints, follows PEP 8, and has NumPy-style docstrings.
- Code examples and reference-code reading assume PyTorch and PyTorch Geometric conventions.
- Math notation: use LaTeX between `$ ... $` for inline math and `$$ ... $$` for display math.
  Never use Unicode math characters (e.g., write `$\theta$` not `θ`).
  Never use `\( ... \)` or `\[ ... \]` — these don't render in GitHub markdown preview.

## Where things live

PaperLab splits files between two locations. Every subagent MUST read `paperlab.config.yaml` at the repo root first to resolve paths.

### Repo (this directory)

- `papers/<slug>/<slug>.pdf` — paper PDF.
- `papers/<slug>/supplementals/` — appendices, supplementary PDFs.
- `papers/<slug>/upstream/<slug>/` — cloned official git repo (if any).
- `sandbox/<slug>/` — toy experiments.
- `paperlab.config.yaml` — per-machine paths (git-ignored). Copy from `paperlab.config.example.yaml`.

### Vault (`vault_paperlab_path` from the config)

All agent-generated files live flat under one folder per paper at `<vault_paperlab_path>/<slug>/`:

- `paper-info.md` — acquisition metadata, includes absolute links to repo-side PDF/upstream.
- `spec.md` — structured extraction from the `dissector` subagent.
- `code_map.md` — mapping from paper concepts to official code from the `implementer` subagent.
- `critic_reviews.md` — audit from the `critic` subagent.
- `<concept>.md` — concept explanation from the `explainer` subagent.
- `synth__<concept_a>__<concept_b>.md` — concept synthesis from the `explainer` subagent.
- `notes.md` — user notes.
- (Later) `slides.md`, `*.tldr`, `*.svg`, `*.png` from the `visualizer` subagent.
- (Later) `tutor_log.md` from the `tutor` subagent.

### Unified file convention

- One schema; no agent-only or user-only file variants. The user reads and may edit any file.
- On regeneration of an existing file, the agent MUST ask before overwriting. See `.cursor/rules/paperlab-regenerate-prompt.mdc`.
- All paper folders follow the same flat structure; no per-paper config files.

### Cross-references

`paper-info.md` (in the vault) includes absolute paths to the repo-side PDF and upstream code, built from `repo_root` in `paperlab.config.yaml`. These links are machine-specific.

## Cursor Subagents

PaperLab uses Cursor project subagents in `.cursor/agents/`.

- `acquirer` sets up the per-paper repo folder (`papers/<slug>/`) and vault folder (`<vault>/<slug>/`), downloads PDFs/supplements, clones upstream repos, and writes `paper-info.md` to the vault.
- `dissector` reads the paper PDF and writes `spec.md` to the vault.
- `implementer` maps paper concepts to official code and writes `code_map.md` to the vault; deep-dive mode writes `code_map__<slug>__<component>.md`.
- `explainer` writes single-concept explanation files or synthesis files to the vault.
- `critic` audits claims, reproducibility, and paper-code alignment, then writes `critic_reviews.md` to the vault.
- `visualizer` produces a Marp slide deck (`slides.md`) summarizing the paper, or a standalone per-concept visualization (`<concept>__viz.md`). Defaults to Mermaid + Marp (theme `gaia`); escalates to TikZ / matplotlib SVG / tldraw `.tldr` only with stated justification.

## Agent-To-Skill Mapping

Each subagent must read its corresponding skill before task-specific work:

- `acquirer` → `.cursor/skills/ml-acquisition/SKILL.md`
- `dissector` → `.cursor/skills/ml-paper-spec/SKILL.md`
- `implementer` general mode → `.cursor/skills/ml-code-map/SKILL.md`
- `implementer` deep-dive mode → `.cursor/skills/ml-code-map/DEEP_DIVE.md`
- `critic` → `.cursor/skills/ml-critique/SKILL.md`
- `explainer` single-concept mode → `.cursor/skills/ml-explanation/SKILL.md`
- `explainer` synthesis mode → `.cursor/skills/ml-synthesis/SKILL.md`
- `visualizer` (both modes) → `.cursor/skills/ml-visualization/SKILL.md`

Treat those skills as authoritative for output structure, naming, scope boundaries, and self-checks.

## Suggested Workflow

For each paper:

1. Use the `acquirer` subagent with `<slug>` and `<paper-url>`.
2. Use the `dissector` subagent to produce `spec.md`.
3. Use the `implementer` subagent to produce `code_map.md`, if upstream code exists.
4. Use the `critic` subagent to produce `critic_reviews.md`.
5. Use the `explainer` subagent on demand for concepts or syntheses.
6. Use the `visualizer` subagent for a slide deck or per-concept diagram.

## Uncertainty Rule

When a paper is ambiguous or information cannot be determined from the source, flag it explicitly rather than guessing. Prefix such flags with:

`⚠️ UNCERTAIN:`

## Sandbox

Test algorithms and experiments in `sandbox/`.