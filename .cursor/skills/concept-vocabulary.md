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

### centrality
- Aliases: node centrality, centrality measures
- First seen: GNR (2026-06-02)

### graph-convolutional-network
- Aliases: GCN, graph convolutional networks, graph convolutional neural networks
- First seen: M-RCNN (2026-06-02)

### graph-attention-network
- Aliases: GAT, graph attention networks
- First seen: GNR (2026-06-02)

### knowledge-graph
- Aliases: KG, knowledge graphs, multi-relational graph
- First seen: GENI (2026-06-02)

### predicate-aware-attention
- Aliases: predicate-aware attention mechanism, relation-aware attention
- First seen: GENI (2026-06-02)

### gravity-model
- Aliases: gravity centrality, gravity law, multi-characteristics gravity model, MCGM
- First seen: SIR (2026-06-02)

### graph-neural-network
- Aliases: GNN, graph neural networks
- First seen: GNR (2026-06-02)

### network-dismantling
- Aliases: network dismantling, graph dismantling
- First seen: GNR (2026-06-02)

### node-ranking
- Aliases: node ranking, influential node identification
- First seen: GNR (2026-06-02)

### shannon-entropy
- Aliases: Shannon entropy, node entropy, information entropy
- First seen: EDDC (2026-06-02)

### sir-epidemic-model
- Aliases: SIR model, susceptible-infected-recovered, epidemic spreading dynamics
- First seen: SIR (2026-06-02)
