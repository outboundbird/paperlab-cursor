# PaperLab: Agent-Assisted Reading Of ML Methods Papers

PaperLab helps the user understand mathematics in machine learning and deep learning papers.

## Project Conventions

- Python code uses type hints, follows PEP 8, and has NumPy-style docstrings.
- Code examples and reference-code reading assume PyTorch and PyTorch Geometric conventions.
- Papers are stored under `papers/`.
- Paper folders use `papers/<slug>`.
- Math notation: use LaTeX between `$ ... $` for inline math and `$$ ... $$` for display math.
  Never use Unicode math characters (e.g., write `$\theta$` not `θ`).
  Never use `\( ... \)` or `\[ ... \]` — these don't render in GitHub markdown preview.

Each paper folder may contain:

- `<slug>.pdf` — the paper itself
- `paper-info.md` — acquisition metadata
- `spec.md` — structured extraction from the Dissector subagent
- `code_map.md` — mapping from paper concepts to official code from the Implementer subagent
- `critic_reviews.md` — audit from the Critic subagent
- `<concept>.md` — concept explanation from the Explainer subagent
- `synth__<concept_a>__<concept_b>.md` — concept synthesis from the Explainer subagent
- `notes.md` — user notes
- `upstream/` — cloned official GitHub repo, if available

## Cursor Subagents

PaperLab uses Cursor project subagents in `.cursor/agents/`.

- `acquirer` sets up `papers/<slug>/`, downloads PDFs/supplements, clones upstream repos, and writes `paper-info.md`.
- `dissector` reads the paper PDF and writes `spec.md`.
- `implementer` maps paper concepts to official code and writes `code_map.md`; deep-dive mode writes `code_map__<slug>__<component>.md`.
- `explainer` writes single-concept explanation files or synthesis files.
- `critic` audits claims, reproducibility, and paper-code alignment, then writes `critic_reviews.md`.

## Agent-To-Skill Mapping

Each subagent must read its corresponding skill before task-specific work:

- `acquirer` → `.cursor/skills/ml-acquisition/SKILL.md`
- `dissector` → `.cursor/skills/ml-paper-spec/SKILL.md`
- `implementer` general mode → `.cursor/skills/ml-code-map/SKILL.md`
- `implementer` deep-dive mode → `.cursor/skills/ml-code-map/DEEP_DIVE.md`
- `critic` → `.cursor/skills/ml-critique/SKILL.md`
- `explainer` single-concept mode → `.cursor/skills/ml-explanation/SKILL.md`
- `explainer` synthesis mode → `.cursor/skills/ml-synthesis/SKILL.md`

Treat those skills as authoritative for output structure, naming, scope boundaries, and self-checks.

## Suggested Workflow

For each paper:

1. Use the `acquirer` subagent with `<slug>` and `<paper-url>`.
2. Use the `dissector` subagent to produce `spec.md`.
3. Use the `implementer` subagent to produce `code_map.md`, if upstream code exists.
4. Use the `critic` subagent to produce `critic_reviews.md`.
5. Use the `explainer` subagent on demand for concepts or syntheses.

## Uncertainty Rule

When a paper is ambiguous or information cannot be determined from the source, flag it explicitly rather than guessing. Prefix such flags with:

`⚠️ UNCERTAIN:`

## Sandbox

Test algorithms and experiments in `sandbox/`.