---
name: ml-visualization
description: Defines the schema for concept pictures produced from an ML paper — one PNG per concept, dictionary-driven, rendered via graphviz on a 4:3 canvas. Writes to `vault_path(slug, f"figures/{concept}.png")`. Use when drawing, visualizing, or picturing a specific concept, algorithm, or workflow from a paper.
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
7. **Render** via `python -m tools.visualize_concept <spec.yaml> <out.png>` → graphviz writes `.png` + `.svg` + `.dot`. The renderer enforces the 4:3 canvas and emits the legend.
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

Concept pictures are rendered on a **4:3 canvas envelope** (9.6 × 7.2 inches at 160 DPI = 1536 × 1152 PNG). This is the slide-friendly target — wider aspect ratios encourage left-to-right chains that lose vertical structure (loop frames, side-incoming reparameterise arrows, parameter annotations).

The 4:3 envelope is the **outer canvas**, not the main graph's bounding box. The renderer enforces it via graphviz `size="9.6,7.2!"` plus an aspect-ratio pad (`ratio=0.75`) so the output PNG is always 4:3 regardless of the natural layout.

### Dictionary-tag discipline — legend, not inline tags

Nodes carry **only** their role-specific label (e.g., `Z_X^(l-1)`, `P(Z_A^(l) | A, Z_X^(l-1))`, `θ ❄ (frozen)`). Edges carry their semantic label only (`condition`, `sample`, `param-by`). Dictionary codes (`E5`, `A7`, …) are **not** drawn next to the glyphs; the visual idiom (shape, color, line style) is the tag.

Instead, every picture carries a **legend panel** on the right edge of the canvas. The legend lists each distinct dictionary entry that appears in the picture, alongside:

- a miniature instance of the glyph in the picture's own style (swatch for entities, coloured line for relations/actions), and
- the **canonical name from `DICTIONARY.md`, verbatim** — the wording in the "Canonical name" column, exactly as written there. The legend does **not** display dictionary codes (`E14`, `R1`, `A5`, …) and does **not** annotate canonical names with styling qualifiers like `(dotted)` or `(dashed)`. Those are renderer-internal details.

The renderer emits the legend automatically from the set of dictionary IDs in the spec — no extra authoring required.

### Canvas layout

The 4:3 canvas is partitioned into two side-by-side regions:

- **Left region (≈ 75% width):** the main concept picture, laid out left-to-right per the spec's `rankdir` (typically `LR`). All concept nodes, edges, clusters, and the title sit here.
- **Right region (≈ 25% width):** the legend panel, a single vertical column of legend rows pinned to the right edge.

The two regions together fill the 4:3 envelope. The renderer pins the legend rightward via `rank="sink"` plus an invisible anchor edge. The legend never sits above or below the main graph and never overlaps it.

If the spec genuinely doesn't fit (rare — usually means the spec is overgrown and wants splitting into two pictures), the agent escalates to the user rather than silently switching aspect ratios or shrinking the legend.

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

- **Math notation in labels:** Unicode characters only (`Σ`, `μ`, `σ`, `θ`, `ε`, `zₜ`, `Z⁽ˡ⁾`, `≤`, `≥`, `∑`). Graphviz does not render LaTeX. Compound math (fractions, expectations with subscripted distributions) belongs in the prose around the picture, not in node labels.
- **No LaTeX in spec labels** — no `$...$`, no `\frac`, no `\mathbb`, no `\mathcal`, no backslash-prefixed math commands.
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
- **Legend hygiene.** Every dictionary ID used appears in the legend; canonical names are verbatim; no codes (`E5`, `A7`); no styling qualifiers (`(dotted)`, `(dashed)`).
- **Aspect ratio.** The rendered PNG's W:H is 4:3 ± 5%. If not, the renderer is misconfigured — escalate before delivering.
- **Thesis re-read.** State the thesis aloud (mentally) and trace it through the picture. If you can't, the spec doesn't argue the thesis — fix the spec, not the picture.

## Reporting back

After writing the spec and rendering, respond with:

- **Picture path** (`<vault>/<slug>/figures/<concept>.png`) and **spec path** (`<vault>/<slug>/figures/<concept>.spec.yaml`).
- **Thesis sentence** chosen.
- **Dictionary inventory** (the three-column table from step 3), compact.
- **Gap-rule applications**, if any.
- **`⚠️ UNCERTAIN:` flags** raised, if any.
- **Rendered PNG aspect ratio** (W:H, computed from the actual file dimensions) — for catching renderer regressions.
- **Hand-off note** to `figure-verifier`: "Ready for verification" (or "verifier not yet shipped — stopping at self-verify").
