# Concept vocabulary

Shared, controlled list of canonical concept names for the `concepts:`
front-matter key and `[[wiki-link]]` references across PaperLab artifacts.

## Why this exists

`concepts:` edges are only useful if every agent links the *same* concept by
the *same* name. Without a controlled list, the same idea drifts into variants
(`IB` vs. `Information Bottleneck` vs. `information-bottleneck`), and the future
graph index (`reindex.py`, see `ROADMAP.md`) cannot connect papers that share a
concept. This file is the single source of canonical names.

## How agents use it

- **Grown on demand.** This list is not pre-seeded. When an agent references a
  concept, it checks this list first.
- **Reuse before coining.** If a canonical name already fits, link to it. Only
  add a new entry when no existing name matches.
- **Append, never rename.** Renaming a canonical name breaks every existing
  `[[wiki-link]]`. Add aliases instead.
- **Naming convention.** Lowercase, hyphen-separated, singular
  (`information-bottleneck`, `mutual-information`, `message-passing`). The
  `[[wiki-link]]` uses this exact string.

## Format

One entry per concept:

```markdown
### <canonical-name>
- Aliases: <comma-separated alternative names seen in papers>
- First seen: <slug> (<YYYY-MM-DD>)
```

## Concepts

<!-- Append new concepts below. Keep alphabetical by canonical name. -->
