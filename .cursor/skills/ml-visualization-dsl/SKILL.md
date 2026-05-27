---
name: ml-visualization-dsl
description: Defines the operator-tree DSL for concept pictures — a compositional alternative to the graphviz node/edge schema. Operators (Juxtapose, Decompose, Leaf) carry spatial intent (comparison, factorization, atomic placement) that the matplotlib renderer enforces. Use when drawing a concept picture and the source text has clear compositional structure (factorization, side-by-side comparison, whole-to-parts), or when the graphviz path collapsed into a flowchart.
---

# Concept-picture DSL — operator-tree schema

## Why this exists

The graphviz path (`ml-visualization/SKILL.md`) treats every figure as a flat node/edge layout. It produces flowcharts even when the source text argues a factorization or a comparison, because graphviz has no operator for those intents. This skill defines a small DSL of *compositional operators* the agent picks before placing any atoms: the operator carries the spatial intent, and the renderer (`tools.render_dsl`) owns the layout.

The DSL is intentionally small in Phase 1: three operators. The vocabulary grows one operator at a time, each motivated by a real paper figure that needed it. Resist the urge to invent new operators speculatively.

## The three operators

### `Leaf(dict_id, label)`

The atomic unit. Renders one dictionary entry (E*, R*, A* — see `ml-visualization/DICTIONARY.md`) with a paper-notation label drawn inside. The renderer picks the visual idiom (shape, palette, glyph) from `dict_id`.

```yaml
op: Leaf
dict_id: E5
label: "q(z | x)"
```

Label discipline (this is the rule the graphviz path got wrong): **labels are names, not values.** Paper notation only. No numerical values, no comma-separated tuples, no algebraic expansions, no `(0.54, 0.24, 0.15, 0.07)`. Worked-example numbers belong in the prose around the picture, not on the picture.

### `Juxtapose(left, right, title=?, gutter=?)`

Two sub-pictures side by side. **Intent: comparison.** The reader is meant to read `left` and `right` as two views of the same idea, not as a sequential dataflow. The renderer draws each side on its own pale panel with optional sub-title; there is no arrow between them.

```yaml
op: Juxtapose
title: "encoder vs decoder factorizations"
left:
  op: Decompose
  ...
right:
  op: Decompose
  ...
```

When to reach for it:
- Paper shows a global view next to a local view (architecture diagram next to a single layer's detail).
- Paper compares two distributions, two losses, two architectures.
- Paper shows a "before" state next to an "after" state of the same object.

When **not** to reach for it:
- Paper shows a pipeline `A → B → C`. That's not a comparison; it's a sequence. (Phase 1 doesn't have a `Pipeline` operator; if you have a true sequence and no comparison, you may need to fall back to the graphviz path until `Pipeline` is added.)

### `Decompose(whole, parts, title=?, relation="=")`

A whole on the left; its parts stacked on the right; joined by a curly brace carrying the `relation` label. **Intent: factorization, or whole-to-parts.** The reader is meant to read `whole ≡ part_1 ⋄ part_2 ⋄ ...` where `⋄` is whatever the paper specifies (chained conditionals, product, sum, ...).

```yaml
op: Decompose
title: "encoder"
relation: "factors as"
whole:
  op: Leaf
  dict_id: E5
  label: "q(z | x)"
parts:
  - { op: Leaf, dict_id: E1, label: "μ_φ(x)" }
  - { op: Leaf, dict_id: E1, label: "log σ²_φ(x)" }
```

Constraints:
- `parts:` must have **two or more** entries. One part means there's no factorization; use a `Leaf` directly.
- Parts appear top-to-bottom on the canvas in the order they appear in the YAML.
- `relation` is a short italic label drawn on the connector between whole and brace. Defaults to `"="`. Use `"factors as"`, `"=∏"`, `"=∑"`, `"i.i.d. per node"`, etc. — whatever the paper uses.

When to reach for it:
- Paper writes a joint as a product of conditionals: `p(z, x) = p(z) p(x | z)`.
- Paper splits a quantity into named heads (encoder outputs μ and log σ²).
- Paper writes a distribution as i.i.d. per index.

When **not** to reach for it:
- Paper writes a sum or a single transform with multiple inputs; that's a dataflow, not a decomposition.

## Authoring workflow

Same four-decision composition step as the graphviz path (`ml-visualization/SKILL.md` "Picture composition"), but the output is an operator tree, not a node/edge list.

1. **Headline.** One subject-verb-object sentence in the paper's vocabulary. If you can't write it, the picture isn't ready.
2. **Cast (≤ 6 typed actors).** The load-bearing entities the picture stages. Each cast member becomes a `Leaf` somewhere in the tree.
3. **Top-level operator.** Read the headline and pick:
   - Headline says "compares" / "two views of" / "global vs local" → `Juxtapose`.
   - Headline says "factorizes" / "splits into" / "decomposes" / "is the product of" → `Decompose`.
   - Headline names a single thing → `Leaf` is the whole picture (rare; usually the picture has internal structure).
4. **Recurse.** For each operator argument, decide if it is itself composite. Stop when every leaf-slot has a `Leaf` atom.

Resist nesting beyond two operators in Phase 1. If the tree wants three nested operators, you are probably trying to express a pipeline or a loop; that's a sign the operator set is insufficient — flag it and use the graphviz path for now.

## Schema reference

Top-level:

```yaml
title: "<top-level caption>"          # optional
slug: "<paper slug>"                   # optional; verbatim user input
output: "<concept-or-pseudocode-name>" # optional; bare name, `.png` appended

root:
  op: <one of Leaf | Juxtapose | Decompose>
  ...                                  # operator-specific fields
```

Output path resolution is the same as the graphviz path: if the CLI is invoked with an explicit `out.png` argument, it wins; otherwise the renderer joins `vault_path(slug, "figures/")` with `output + ".png"`.

## Operator-picking guide (decision tree)

```
Does the headline compare two things?
├── Yes → Juxtapose(left, right)
│        ├── Are the two things themselves composite?
│        │   └── Yes → recurse (Decompose / Juxtapose inside each side)
│        └── No → Leaf inside each side
│
└── No, the headline factorizes one thing?
    ├── Yes → Decompose(whole, parts)
    │        ├── Are the parts composite?
    │        │   └── Yes → recurse
    │        └── No → Leaf inside each part
    │
    └── No, the headline names one atom?
        └── Leaf
```

If none of the three operators fit, **stop and report**. Do not force a tree that doesn't match the headline. The honest answer "this concept needs an operator the DSL doesn't have yet" is more useful than a stretched fit.

## Self-checks before rendering

- ✅ `headline:` (kept in a comment if the spec doesn't have a header field) is a real subject-verb-object sentence.
- ✅ Every cast member appears as a `Leaf` somewhere in the tree.
- ✅ No `Leaf.label` contains numerical values or comma-separated tuples.
- ✅ `Decompose.parts` has ≥ 2 entries.
- ✅ Tree depth is ≤ 2 (Phase 1 limit).
- ✅ Picture argues the headline. If a reader with only the headline and the picture cannot restate the claim, the tree is wrong; rewrite the tree, not the renderer settings.

## Rendering

```
python -m tools.render_dsl <spec.yaml> [<out.png>]
```

Output dimensions and aspect ratio are determined by the tree's natural size; there is no fixed canvas. Inspect the resulting PNG and the rendered shapes/labels against the self-check list before handing back to the user.

## Phase boundaries

This skill describes Phase 1 of the DSL: three operators, matplotlib backend, no agent verifier. The roadmap to Phase 2 (Inset, RingOf, Plate, Callout, BeforeAfter operators), Phase 3 (TikZ backend for typographic quality), and Phase 4 (figure-verifier subagent) is intentionally not in this skill — those operators arrive one paper at a time, motivated by a concrete figure the current DSL cannot express.
