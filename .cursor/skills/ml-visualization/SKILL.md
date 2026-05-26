---
name: ml-visualization
description: Defines the schema for concept pictures produced from an ML paper — one PNG per concept, dictionary-driven, rendered via graphviz with a composed side-legend layout. Writes to `vault_path(slug, f"figures/{concept}.png")`. Use when drawing, visualizing, or picturing a specific concept, algorithm, or workflow from a paper.
---

# ML Visualization Schema

## Purpose

This file defines the schema for **concept pictures** produced by the Visualizer subagent: one PNG per concept, derived from `<concept>.md` (or a pseudocode block in `spec.md` §6) by running the dictionary-driven cascade and rendering via graphviz to `vault_path(slug, f"figures/{concept}.png")`.

The Visualizer never produces slide decks, Marp output, Mermaid diagrams, or TikZ. It produces exactly one artifact per invocation: a single concept picture. It never modifies `spec.md`, `code_map.md`, or `<concept>.md` content; it only appends an embed link to `<concept>.md` if one is not already present.

## Concept-picture workflow (dictionary-driven)

Fixed cascade. Every picture follows it.

1. **Read the source text.** `<vault>/<slug>/<concept>.md` (preferred — from the `explainer`) or a passage from `<vault>/<slug>/spec.md` §6 (a pseudocode block). Read all of it, including any worked example.
2. **State the thesis.** One sentence: what is the picture *for*? Expressed in the paper's own vocabulary. Test: a reader who walks away with only the picture and the thesis should be able to restate the claim.
3. **Inventory against `DICTIONARY.md`.** Walk the source text top to bottom; for each named thing (noun, verb, relation) find its dictionary entry. Build a three-column table: *concept in the text → dictionary entry (E/R/A id) → notes*. **Text-driven, not dictionary-driven** — never scan the dictionary asking "could I use this entry here?", that produces clip-art.
4. **Apply the gap rule** for any concept that doesn't fit an entry. Cascade (in `DICTIONARY.md`): (1) compose from primitives, (2) draw the closest entry with a label, (3) text-arrow fallback `— [verb objective] →`, (4) stop and report. Never invent a new symbol silently.
5. **Honor the atomicity rule.** Each dictionary action (A1, A5, A7, …) is **one arrow**. Sub-operations that exist only to feed the action ride as annotations on the action's arrow, not as separate arrows or nodes.
6. **Emit the picture spec** as YAML at `vault_path(slug, f"figures/{concept}.spec.yaml")`: title, optional thesis, rankdir, nodes (`id`, `dict_id`, `label`), edges (`src`, `dst`, `dict_id`, `label`), optional clusters (loop frames). The spec is the audit trail for steps 2–5.
7. **Render** via `python -m tools.visualize_concept <spec.yaml> [<out.png>]` → only the final composed PNG lands on disk; figure/legend intermediates are written to a tempdir and deleted on success. The CLI `out` argument is optional: when omitted, the renderer resolves it from the spec's `slug:` and `output:` keys (see "Output naming" below). Default mode (`--legend side`) lays the figure top-to-bottom on the left and the legend panel on the right, joined via PIL. Use `--legend inline` to fall back to the legacy single-graph 4:3 layout, or `--legend none` to render the figure only.
8. **Self-verify against the thesis.** Re-read step 2. If the picture doesn't argue the thesis sentence, the spec is wrong; do not paper over with backend tweaks. Common spec errors:
   - Thesis claims a *layered cascade*, spec collapsed two stages into one node.
   - Thesis claims a *factorization*, spec drew it as a single arrow.
   - Thesis describes *what changes per iteration*, spec drew only one iteration with no loop frame.
9. **Hand off to `figure-verifier`** (when that subagent ships — see ROADMAP §3). Until then, stop after step 8.

### What the dictionary is (and what it is not)

**The dictionary is a style guide, not a clip-art library.** Each entry tells the agent *how to draw an instance of that concept in this project's visual language* — a vector chip is a small box with these proportions and colors; a conditional distribution is an ellipse with incoming conditioning arrows; a frozen parameter is a dashed box with a snowflake glyph.

When the renderer encounters a node tagged `E1 vector` with label `Z_X^(l-1)`:

- ✅ **Correct:** draws a vector-shaped node in the project's palette, with `Z_X^(l-1)` as the node's label *inside* the shape.
- ❌ **Wrong:** pastes `symbols/E1.png` (the dictionary's *example* drawing) as the node body. This produces a Frankenstein collage where every node is at a different scale and the labels float untethered.

The user-drawn `symbols/<id>.png` files live inside `DICTIONARY.pdf` as the reference card. **They are not assets the renderer pastes into output.** A concept picture redraws each atom inline.

Mental model: the dictionary is to a concept picture what a typography style guide is to a printed page. The style guide says "headings are 14pt Helvetica bold, dark blue" — it does not supply pre-rendered PNG screenshots of every heading. The page setter reads the style guide and types the heading at the right place on the page.

### Canvas aspect ratio

Concept pictures are rendered in **composed mode** by default: graphviz lays out the figure in TB (top-to-bottom) at the requested font scale (title 56pt, node 48pt, edge 40pt; `penwidth=2.0`, `arrowsize=1.2`), graphviz separately rasterizes the legend panel, and PIL pastes the two side by side with a 60px gutter. There is **no fixed aspect ratio**; the resulting PNG is whatever shape the content dictates (typically ~2:1 landscape — figure-dominant, legend snug on the right).

Why composed instead of a single 4:3 canvas: graphviz `dot` only honors `rankdir` at the top level, so a side-legend on the same canvas forces the whole picture into LR, which crushes vertical structure (loop frames, reparameterise arrows, parameter annotations). Composing two graphs decouples figure-layout from legend-layout — both panels keep their natural shape and their natural font sizes.

The legacy single-graph 4:3 layout (`--legend inline`) is preserved as a fallback for cases where a slide-friendly fixed-aspect output is required.

### Dictionary-tag discipline — legend, not inline tags

Nodes carry **only** their role-specific label (e.g., `Z_X^(l-1)`, `P(Z_A^(l) | A, Z_X^(l-1))`, `θ ❄ (frozen)`). Edges carry their semantic label only (`condition`, `sample`, `param-by`). Dictionary codes (`E5`, `A7`, …) are **not** drawn next to the glyphs; the visual idiom (shape, color, line style) is the tag.

Every picture carries a **legend panel** on the right edge of the canvas listing each distinct dictionary entry used in the picture.

### Legend wording — paper notation, not dictionary canonical name

Each legend row has the form:

```
[swatch / line]    <paper notation>  —  <context phrase>
```

Where:

- **Paper notation** = the first-occurring node/edge `label` in the spec for that `dict_id`, rendered through the renderer's math translator so sub/superscripts (`Z_X^(l-1)`) come out as proper subscripts.
- **Context phrase** = a 2–6 word noun phrase in the paper's vocabulary (`adjacency matrix`, `feature latent (previous layer)`, `structural conditional`, `Gaussian noise (reparameterise)`, …). Sourced from the first-occurring node/edge's `legend_context` field. If empty, only the paper notation is shown.

**The legend does NOT show the dictionary's canonical name.** The canonical name (e.g., "graph edge / adjacency", "conditional distribution") is the renderer's internal vocabulary for shape lookup; readers should see the paper's wording, not the dictionary's. The legend also never shows dictionary codes (`E14`, `R1`, `A5`) or styling qualifiers (`(dotted)`, `(dashed)`).

**Provenance.** The `legend_context` phrase must be traceable to the source text — verbatim or close paraphrase from `<concept>.md` or `spec.md`. Agent-invented jargon ("relay variable", "structural seed") fails the provenance self-check below.

**Override mechanism.** When the first-occurring `label` is too verbose for the legend (e.g., a 40-character compound expression), the spec may include a top-level `legend:` block to override per `dict_id`:

```yaml
legend:
  - dict_id: E5
    label: "P(· | ·)"                       # override the legend label only
    legend_context: "conditional (per stage)"  # override the context phrase
```

Either field is optional. When the override block is absent, first-occurrence rules apply.

### Picture-spec schema

The picture-spec YAML carries:

```yaml
title: "<short caption>"
thesis: "<one-sentence thesis>"            # optional but recommended
rankdir: LR                                # or TB (composed mode forces TB)
slug: "<paper slug>"                       # optional; pairs with `output:` below
output: "<concept-or-pseudocode-name>"     # optional; bare name, `.png` appended

nodes:
  - id: <local_id>
    dict_id: <E*>
    label: "<role-specific label, math syntax allowed>"
    legend_context: "<2–6 word context phrase>"   # optional; used on first occurrence

edges:
  - src: <node_id>
    dst: <node_id>
    dict_id: <R*/A*>
    label: "<semantic label>"
    legend_context: "<2–6 word context phrase>"   # optional

clusters:                                  # optional, for loop frames (E12/A10)
  - id: <local_id>
    label: "<frame label>"
    contains: [<node_id>, ...]

legend:                                    # optional, overrides per dict_id
  - dict_id: E5
    label: "<short legend label>"
    legend_context: "<short context phrase>"
```

No `shape`, `color`, `style`, or any styling fields — those are the renderer's responsibility per `dict_id`.

### Output naming

The renderer is path-dumb: it writes one PNG to whatever path it's told and discards all intermediates. The path is resolved in this order:

1. **CLI positional `out`** — when present, used verbatim.
2. **Spec `output:` + `slug:`** — when both are present and `out` is omitted, the renderer resolves `vault_path(slug, f"figures/{output}.png")` via `tools/paths.py`. Bare names without an extension get `.png` appended; explicit extensions are honored.
3. Otherwise the renderer errors and asks for one of the above.

The naming convention itself lives in the caller:

- `visualizer` subagent: `slug: <slug>`, `output: <concept>` → `<vault>/<slug>/figures/<concept>.png`.
- `dissector` (auto-invoked on §6 pseudocode blocks): `slug: <slug>`, `output: <slug>-<pseudocode-id>` → `<vault>/<slug>/figures/<slug>-<pseudocode-id>.png`.

Intermediate figure/legend PNGs (and their `.dot`/`.svg` byproducts) are written to a tempdir during composed-mode render and deleted on success — only the final composed PNG remains on disk. The legacy `--legend inline` and figure-only `--legend none` modes still leave a sibling `.dot` (and `.svg` unless `--no-svg`) next to the output for hand-tuning.

### Canvas layout

The composed canvas is two side-by-side regions:

- **Left region (figure):** the main concept picture, forced to top-to-bottom (`rankdir=TB`) in composed mode regardless of what the spec says. All concept nodes, edges, clusters, and the title sit here. (The spec's `rankdir` field is still honored when using `--legend inline`.)
- **Right region (legend):** the legend panel, a single vertical column of legend rows (40×24 swatches, 36pt body text, 44pt bold "Legend" header).

The two regions are rendered as separate graphviz invocations and joined by PIL with a 60px gutter and vertical center-alignment. The combined PNG is typically landscape (~2:1) but its exact dimensions depend on the content.

If the figure overflows what reads comfortably at the default scale (rare — usually means the spec is overgrown and wants splitting into two pictures), the agent escalates to the user rather than silently shrinking glyphs.

### Worked example

Given `<vault>/GIB/markov-representation.md` and the request "draw the per-layer relay cell":

1. **Read** the whole file, especially §1 Definition, §4 Formal statement, §5 Worked example, and the Algorithm-1 mapping table.
2. **Thesis.** "Each GIB layer factorizes into two stages: first sample a structural latent `Z_A^(l) ~ P(· | A, Z_X^(l-1))`, then a feature latent `Z_X^(l) ~ P(· | Z_X^(l-1), Z_A^(l))` — the layered factorization is what makes per-layer compression bounds tractable."
3. **Inventory** (in source order):
   - "graph $D = (A, X)$" → E14 (adjacency) + E1 (features)
   - "feature latent $Z_X^{(l)}$" → E1 vector
   - "structural latent $Z_A^{(l)}$" → E14 (edge subset, stochastic variant)
   - "$P(Z_A^{(l)} \mid A, Z_X^{(l-1)})$" → E5 conditional distribution
   - "$P(Z_X^{(l)} \mid Z_X^{(l-1)}, Z_A^{(l)})$" → E5 conditional distribution (**second instance — do not merge**)
   - "sample" (×2, one per conditional) → A1 × 2
   - "$\theta$ frozen" → E7 + A20
   - "for each layer $l = 1, \ldots, L$" → E12 / A10 loop frame
4. **Gap rule.** "Local-dependence assumption" is a *property* of the chain, not an atom — annotation on the layer frame.
5. **Atomicity.** Each A1 is one arrow. The transform $\tilde{Z}_X^{(l-1)} = \tau(\cdot)W^{(l)}$ rides as an annotation on the conditioning arrow into the second conditional, not a separate node.
6. **Spec.** 8 nodes (A, Z_X^(l-1), θ, P_ZA, Z_A^(l), P_ZX, ε, Z_X^(l)), 7+ edges, one cluster declaring the layer-l loop frame.
7. **Render** via graphviz.
8. **Self-verify.** Two distinct E5 nodes chained `Z_X^(l-1) → P_ZA → Z_A^(l) → P_ZX → Z_X^(l)`? If only one conditional, the cascade collapsed and the thesis is unmet — fix the spec.

## Conventions

- **Math notation in labels:** use LaTeX-style `_` / `^` for sub/superscripts; the renderer translates them into graphviz HTML `<SUB>` / `<SUP>`. Supported forms:
  - Single-char: `Z_X`, `X^l`.
  - Braced: `Z_{X,v}`, `X^{(l-1)}`.
  - Parenthesised (parens preserved): `Z_X^(l-1)`, `P(Z_A^(l) | A, Z_X^(l-1))`.

  Greek letters and operator glyphs use Unicode (`θ`, `ε`, `μ`, `σ`, `Σ`, `∑`, `≤`, `≥`, `❄`, `⋅`). Do **not** use `$...$` delimiters. Do **not** use backslash commands (`\frac`, `\mathbb`, `\mathcal`, `\tilde`, …) — they are passed through verbatim and won't render. Compound math (fractions, expectations with subscripted distributions) belongs in the prose around the picture, not in node labels.
- **Font.** The renderer uses `fontname="Segoe UI,DejaVu Sans,sans-serif"` on graph / node / edge defaults to cover Greek, sub/superscripts, and the ❄ snowflake.
- **Path resolution:** every path is constructed via `tools/paths.py`. The Visualizer never hard-codes paths.
- **Slug:** verbatim user input. Never normalize.

## Graphviz authoring

When emitting the picture spec, the agent should know what the renderer will do with it:

- **Backend:** `tools.visualize_concept.render(spec_path, png_path)` (or CLI: `python -m tools.visualize_concept <spec.yaml> <out.png>`). Resolves the `dot` binary via `tools.paths.graphviz_dot()` — uses the portable Windows binary if present, else falls back to system `dot`.
- **Node style per `dict_id`** is encoded in the renderer's `_NODE_STYLE` table (shape, fill color, stroke). The agent does **not** specify shape/color in the spec — only `dict_id` and `label`. Style is the renderer's responsibility, derived from the dictionary recipe.
- **Edge style per `dict_id`** likewise (color, line style, arrowhead) via `_EDGE_STYLE`. The agent specifies `dict_id` and `label`; style is automatic.
- **Atomicity** is enforced at the spec level: one action verb in the source text → one edge with that action's `dict_id`. The renderer trusts the spec; the agent owns the rule.
- **Outputs per render:** `<name>.png` (deliverable), `<name>.svg` (resolution-independent backup), `<name>.dot` (source for regeneration).

## Scope boundaries

- **No slide decks, no Marp, no Mermaid, no TikZ, no matplotlib SVG, no tldraw.** If the user asks for slides or a deck, redirect: "The PaperLab visualizer only produces concept pictures (one PNG per concept). Slide-deck generation is out of scope."
- No modification of `spec.md`, `code_map.md`, or the prose of `<concept>.md`. The visualizer may **append** an embed link (`![](figures/<concept>.png)`) to `<concept>.md` if not already present.
- No new runnable code; the experimenter handles that.
- No invented content. If a picture would require asserting something not in the source text, drop the asserted element or flag `⚠️ UNCERTAIN:`.

## Self-check (before reporting back)

Run these mentally before declaring the picture done. Each maps to a failure mode we have actually hit.

- **Dictionary coverage.** Every `dict_id` in the spec resolves in `DICTIONARY.md`. Unknown `dict_id`s fail the check.
- **Atomicity.** Each action verb in the source text appears as exactly one edge in the spec. Two arrows for one verb = atomicity violation. Zero arrows for a verb explicitly named in the thesis = under-drawing.
- **Cascade integrity.** If the thesis says "A causes B causes C", the picture has three distinct nodes A, B, C connected `A → B → C`. Two `E5`s collapsed into one is the canonical failure here.
- **Loop frame.** If the source text says "for each $l = 1, \ldots, L$" (or equivalent iteration), the picture has an `E12`/`A10` cluster wrapping the per-iteration content.
- **Math rendering.** Spot-check at least one label per `dict_id` on the rendered PNG: subscripts and superscripts must render as proper smaller text, not as raw `_X` / `^(l-1)`.
- **Legend hygiene.** Every dictionary ID used appears in the legend; rows are `<paper notation> — <context phrase>`; no canonical names from the dictionary; no codes (`E5`, `A7`); no styling qualifiers (`(dotted)`, `(dashed)`).
- **Legend-context provenance.** Every `legend_context` phrase is traceable to the source text (verbatim or close paraphrase). Agent-invented jargon fails this check — re-read `<concept>.md` and substitute the paper's wording.
- **First-occurrence sanity.** For each `dict_id`, the first-occurring label in the spec is representative enough to anchor the legend. If E5's first occurrence is a 40-character compound expression, add a `legend:` override with a shorter form.
- **Aspect ratio.** Composed mode (default) produces a landscape PNG; W:H is typically between 1.8 and 2.6. Wildly outside that range usually means the figure has degenerated to a long chain — split the spec into two pictures. (For `--legend inline` only, the W:H should be 4:3 ± 5%.)
- **Thesis re-read.** State the thesis aloud (mentally) and trace it through the picture. If you can't, the spec doesn't argue the thesis — fix the spec, not the picture.

## Reporting back

After writing the spec and rendering, respond with:

- **Picture path** (`<vault>/<slug>/figures/<concept>.png`) and **spec path** (`<vault>/<slug>/figures/<concept>.spec.yaml`).
- **Thesis sentence** chosen.
- **Dictionary inventory** (the three-column table from step 3), compact.
- **Gap-rule applications**, if any.
- **`⚠️ UNCERTAIN:` flags** raised, if any.
- **Rendered PNG aspect ratio** (W:H, computed from the actual file dimensions) — for catching renderer regressions. Composed mode: typically 1.8–2.6; `--legend inline`: 4:3 ± 5%.
- **Hand-off note** to `figure-verifier`: "Ready for verification" (or "verifier not yet shipped — stopping at self-verify").
