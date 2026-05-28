# PaperLab: Agent-Assisted Reading Of ML Methods Papers

PaperLab helps the user understand mathematics in machine learning and deep learning papers.

## YAML front-matter

Every agent-generated markdown file under `<vault>/<slug>/` carries a YAML front-matter with a `paper: <slug>` key (in addition to `category:` and `tags:`). The slug is **verbatim user input** — never normalize, capitalize, or pluralize. If the slug contains any of `:`, `#`, `[`, `]`, `{`, `}`, `,`, `&`, `*`, `!`, `|`, `>`, `'`, `"`, `%`, `@`, `` ` ``, or starts with whitespace or `-`, wrap it in double quotes: `paper: "weird:slug"`. This single key lets Obsidian Dataview / property search group every file (spec.md, code_map.md, tutor_log.md, concept files, ...) for one paper.

## Project Conventions

- Python code uses type hints, follows PEP 8, and has NumPy-style docstrings.
- Code examples and reference-code reading assume PyTorch and PyTorch Geometric conventions.
- Math notation: use LaTeX between `$ ... $` for inline math and `$$ ... $$` for display math.
  Never use Unicode math characters in prose, equation blocks, captions, or any free-form markdown (e.g., write `$\theta$` not `θ`).
  Never use `\( ... \)` or `\[ ... \]` — these don't render in GitHub markdown preview.
  **Exception — Mermaid diagrams.** Mermaid renders node and edge labels as plain text/HTML, not LaTeX; `$\theta$` shows up literally. Inside ```` ```mermaid ```` blocks, Unicode math characters (`θ`, `μ`, `Σ`, `ℝ`, `zₜ`, `∇L`, `∑`, `∫`) are *required* for atomic symbols, and compound expressions (fractions, `\mathbb{E}_{...}[\cdot]`, integrals with limits, plate notation) must be referenced from the label as `(eq. N)` and rendered in the adjacent prose/equation block. When a diagram's labels need full LaTeX (commutative diagrams, `\mathbb`, `\mathcal`, sub/superscripts beyond Unicode), escalate to a ```` ```tikz ```` block instead — TikZ labels render LaTeX natively. The "no Unicode math" rule still applies everywhere outside Mermaid labels (TikZ, prose, equations, captions).

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
- `tutor_log.md` — append-only per-turn breadcrumb log from the `tutor` subagent. Tutor reads this on resume to remember prior sessions.
- `tutor_notes.md` — curated study notes from the `tutor` subagent (user-triggered: "summarize our conversation on \<topic\> to study notes").
- `<concept>.md` — single-concept explanation, written by the `tutor` (composes paper-bound content with general field framing).
- `<concept>-<slug>.md` — paper-bound concept explanation, written by the `explainer` (backend, invoked by `tutor`). Intermediate artifact consumed by the tutor.
- `synth__<concept_a>__<concept_b>.md` — concept synthesis, written by the `tutor`.
- `synth__<concept_a>__<concept_b>-<slug>.md` — paper-bound synthesis intermediate, written by the `explainer` (backend).
- `notes.md` — user notes.

> The `visualizer` subagent (`slides.md`, `*.tldr`, `*.svg`, `*.png`) is **on hold** as of 2026-05-27. See [`visualizer-todo.md`](./visualizer-todo.md) and the archive branch `visualizer` for the previous implementation.

### Unified file convention

- One schema; no agent-only or user-only file variants. The user reads and may edit any file.
- On regeneration of an existing file, the agent MUST ask before overwriting. See `.cursor/rules/paperlab-regenerate-prompt.mdc`.
- All paper folders follow the same flat structure; no per-paper config files.

### Cross-references

`paper-info.md` (in the vault) includes absolute paths to the repo-side PDF and upstream code, built from `repo_root` in `paperlab.config.yaml`. These links are machine-specific.

### Windows path warning for `vault_paperlab_path`

Keep `vault_paperlab_path` ASCII — no emoji, no other non-BMP characters — up to and including the `PaperLab/` segment. Non-BMP characters like `🎓` round-trip badly through Windows shells (cmd.exe cp1252) and Cursor's tool-call layer, causing agents (especially the Tutor) to hang on file-existence checks or report files as missing when they exist. Spaces are tolerated but discouraged. Folders elsewhere in your Obsidian vault — siblings of `PaperLab/`, ancestors above it, and children inside per-paper folders — may contain emoji freely. macOS and Linux are unaffected.

If you currently have an emoji in the path, rename the parent folder (e.g., `Modeling 🎓/PaperLab` → `Modeling/PaperLab`) and update `vault_paperlab_path` to match. The Topics tree at large can keep its emoji conventions; only the segment up to `PaperLab/` matters.

## Cursor Subagents

PaperLab uses Cursor project subagents in `.cursor/agents/`.

- `acquirer` sets up the per-paper repo folder (`papers/<slug>/`) and vault folder (`<vault>/<slug>/`), downloads PDFs/supplements, clones upstream repos, and writes `paper-info.md` to the vault.
- `dissector` reads the paper PDF and writes `spec.md` to the vault.
- `implementer` maps paper concepts to official code and writes `code_map.md` to the vault; deep-dive mode writes `code_map__<slug>__<component>.md`.
- `critic` audits claims, reproducibility, and paper-code alignment, then writes `critic_reviews.md` to the vault.
- `tutor` is the user-facing conversational agent for understanding the paper's concepts. Reads `spec.md` and related vault files, talks with the user, invokes the `explainer` in the background when paper-bound content is missing, and writes `tutor_log.md` (every turn), plus `tutor_notes.md` / `<concept>.md` / `synth__<a>__<b>.md` (only on explicit user request).
- `explainer` is **backend-only as of 2026-05-27**. Invoked by the `tutor`, never by the user. Writes paper-bound intermediates: `<concept>-<slug>.md` (single-concept) or `synth__<a>__<b>-<slug>.md` (synthesis).

## Agent-To-Skill Mapping

Each subagent must read its corresponding skill before task-specific work:

- `acquirer` → `.cursor/skills/ml-acquisition/SKILL.md`
- `dissector` → `.cursor/skills/ml-paper-spec/SKILL.md`
- `implementer` general mode → `.cursor/skills/ml-code-map/SKILL.md`
- `implementer` deep-dive mode → `.cursor/skills/ml-code-map/DEEP_DIVE.md`
- `critic` → `.cursor/skills/ml-critique/SKILL.md`
- `tutor` → `.cursor/skills/ml-tutor/SKILL.md` (also reads `ml-explanation/SKILL.md` and `ml-synthesis/SKILL.md` before writing `<concept>.md` or `synth__<a>__<b>.md`)
- `explainer` single-concept mode → `.cursor/skills/ml-explanation/SKILL.md`
- `explainer` synthesis mode → `.cursor/skills/ml-synthesis/SKILL.md`

Treat those skills as authoritative for output structure, naming, scope boundaries, and self-checks.

## Suggested Workflow

For each paper:

1. Use the `acquirer` subagent with `<slug>` and `<paper-url>`.
2. Use the `dissector` subagent to produce `spec.md`.
3. Use the `implementer` subagent to produce `code_map.md`, if upstream code exists.
4. Use the `critic` subagent to produce `critic_reviews.md`.
5. Use the `tutor` subagent (`/tutor <slug>`) for conversational concept understanding. The tutor invokes the `explainer` in the background as needed; users do not call the explainer directly.

## Uncertainty Rule

When a paper is ambiguous or information cannot be determined from the source, flag it explicitly rather than guessing. Prefix such flags with:

`⚠️ UNCERTAIN:`

## Sandbox

Test algorithms and experiments in `sandbox/`.