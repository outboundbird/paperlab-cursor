# Visualizer — postmortem and side-project spec

> **Status (2026-05-27):** the `visualizer` and `figure-verifier` subagents are **on hold**. After four iterations of architecture changes and ~two weeks of work, the system can produce structurally-correct picture specs but cannot produce figures that read like the hand-drawn references the user kept showing as the quality bar. This document records what was tried, what was learned, and a forward-looking proposal for a side project that could close the gap.

## Why this document exists

PaperLab's visualizer was the most ambitious agent in the project — it had to turn free-form ML paper text into a single PNG whose spatial layout argued the paper's claim. Multiple architectural pivots produced legitimate sub-results (a working dictionary of visual idioms, a label-discipline rule the agent reliably followed, a compositional DSL that surfaced operator gaps honestly), but the *combined output quality* remained well below hand-drawn references. The user's verdict ("I'm starting to believe this task cannot be achieved by agents") deserved a more honest hearing than the iterative loop was giving it.

Rather than continue chasing diminishing returns inside PaperLab, the visualizer is being shelved here and respun as a side project framed as **research, not tooling**. This file is the handoff: chronicle the experiments so future-us doesn't re-derive them, and propose a research framing that doesn't repeat the failure modes.

## Quality bar (what "good" would have looked like)

Two hand-drawn references the user provided during the work:

- A GIB-style architecture figure showing the *Markov chain* of layer-wise latents: `Z_X^(0) → Z_X^(1) → Z_X^(2) → … → Z_X^(L) → ŷ`, with `Z_A^(l)` branching off each transition, "Compression" and "Prediction" frames around segments, and a side panel showing the local view at one layer.

- A GIB-Cat training figure showing the full loss landscape: input adjacency + features → Gumbel-Softmax sampling → KL against `Unif(1/deg)` → message passing → reconstruction → KL against `N(0,1)` → composite loss. Colored frames around sub-objectives, callouts for hyperparameter updates, density curves drawn as small curves (not ellipses).

Both figures are **dataflow graphs with embedded plates, callouts, and intent-bearing frames**. Neither is reachable from the four architectures we tried.

## The four iterations

### Iteration 1 — Graphviz baseline (shipped 2026-05-22, retired in this doc)

**What we built.** `tools/visualize_concept.py` rendering a YAML node/edge spec via graphviz `dot`, with per-`dict_id` shape and palette tables. Composed side-legend layout (two graphviz invocations + PIL).

**Why this seemed right.** Graphviz auto-layout was the cheapest path from "the agent has identified entities and arrows" to "a PNG exists." The dictionary-as-style-guide framing (each dict_id → an inline shape, not a pasted PNG) was a real win — it killed the Frankenstein-collage failure mode of v1.

**What it produced.** Reference: `sandbox/GIB/v3_panel_b.png` (5468×2473, 2.21:1). Clean for the Markov *factorization* spec when hand-authored. When the agent authored the spec from scratch (e.g., the GIB-Cat sampling worked example), output collapsed to flowchart-style: a vertical chain of generic blue boxes connected by labeled arrows. The semantic shape information in the dictionary was present, but the agent over-classified everything into `E1` and `E14` because those are the most generic categories.

**Why we moved on.** Two distinct failure modes:
1. *Flowchart collapse.* Graphviz's only spatial primitive is "place a node, draw an arrow." Every figure ends up looking like every other figure regardless of what the source text argues.
2. *Spreadsheet labels.* The agent put worked-example numerical values into shape labels (`s = (1.5, 0.7, 0.2, -0.5)`), producing a stack of tables connected by arrows. The graphviz SKILL.md said "labels can contain math" — the agent did exactly that.

**Artifacts kept for reference:**
- `tools/visualize_concept.py` (graphviz pipeline, ~1000 lines).
- `.cursor/skills/ml-visualization/SKILL.md` + `DICTIONARY.md` + `DICTIONARY.pdf` + `symbols/` tiles.
- `tools/build_symbol_sheet.py`, `tools/build_dictionary_pdf.py`.

### Iteration 2 — Cast/headline schema (added 2026-05-27 AM)

**What we built.** Added optional top-level `headline:` and `cast:` keys to the picture spec. `cast:` is a ≤ 6-actor list of typed entities the picture stages. `_validate()` in the renderer warns if cast is missing, oversized, or if a load-bearing shape category isn't represented in the cast.

**Why this seemed right.** The diagnosis after iteration 1 was: the agent enumerates every sentence as a box. The fix should be to force the agent to commit to a small set of typed actors *before* drawing. This is a real editorial discipline question; the schema is the place to enforce it.

**What it produced.** Cast warnings did fire correctly on the legacy `markov_panel_b_spec.yaml`. The agent (run via the visualizer subagent) did produce a cleaner cast on a fresh attempt at GIB-Cat sampling — six typed actors instead of twenty. *But the labels still contained numerical values.* The cast schema attacked the right failure mode (over-enumeration); the labels problem (algebra-in-the-glyph) was a different failure mode and the schema didn't address it.

**Why we moved on.** Cast schema is a strict improvement but not the bottleneck. Even with a well-formed cast, the *rendered* picture was still flowchart-shaped because graphviz still owns the spatial layout.

**Artifacts kept for reference:**
- `CastEntry` dataclass in `tools/visualize_concept.py`.
- "Picture composition" section in `.cursor/skills/ml-visualization/SKILL.md`.

### Iteration 3 — Compositional DSL (`Juxtapose` / `Decompose` / `Leaf`)

**What we built.** A new operator-tree DSL with three operators:
- `Leaf(dict_id, label)` — atomic dictionary entry.
- `Juxtapose(left, right)` — two sub-pictures side by side (comparison).
- `Decompose(whole, parts)` — whole on left, parts on right joined by curly brace (factorization).

Implemented in `tools/figure_dsl.py` + `tools/render_dsl.py` with a matplotlib backend, measure/place two-pass layout, per-operator layout functions. Skill at `.cursor/skills/ml-visualization-dsl/SKILL.md`. Three structurally-different stress YAMLs (`sandbox/stress_a*.yaml`, `b`, `c`) all rendered cleanly.

**Why this seemed right.** Graphviz's flowchart bias is structural, not parametric — no amount of prompt discipline gets around "every node is a rectangle and every edge is an arrow." A DSL whose operators *carry spatial intent* (juxtapose means comparison; decompose means factorization) inverts the problem: the agent picks intent, the renderer enforces spatial meaning per operator.

**What it produced.** Two real wins and one fundamental gap:

1. **Win — refuse-and-name.** When the visualizer agent was given a pipeline-shaped concept (GIB-Cat sampling at `t=1, K=4, k=2`) and asked to use the DSL, it correctly refused to force-fit, named the missing operator (`Pipeline`), and fell back to the graphviz path. This was the cleanest "agent honesty" signal we'd had — the DSL's "if none of the operators fit, stop and report" rule actually fired.

2. **Win — label discipline transferred.** The DSL skill said "labels are names, not values." When the agent fell back to graphviz on the pipeline concept, it produced a graphviz spec *with worked-example numbers removed from labels.* The rule transferred between skills.

3. **Gap — wrong operator vocabulary.** `Juxtapose` and `Decompose` express *algebraic* relations (comparison, factorization). Most ML figures are *sequence* relations (Markov chains, MLPs, training loops, dataflow). When the agent rendered GIB Markov representation with the DSL, it picked `Decompose(Decompose)` because the joint distribution factorizes algebraically — but the *picture* the paper draws is a chain, not a factorization. The DSL forced the agent to encode the equation rather than the picture.

**Why we moved on.** The fix was clear in principle ("add `Pipeline`, `Branch`, `Plate` operators") but the deeper signal was that picking the right operator vocabulary requires looking at a corpus of figures and learning what spatial idioms dominate. That's a research project, not a prompt-tuning project. We had also burned through enough iterations that another "add one more operator and try again" felt like the failure mode the user was warning about.

**Artifacts kept for reference:**
- `tools/figure_dsl.py`, `tools/render_dsl.py`.
- `.cursor/skills/ml-visualization-dsl/SKILL.md`.
- `sandbox/dsl_reference.png`, `sandbox/stress_a.png`, `sandbox/stress_b.png`, `sandbox/stress_c.png` — these demonstrate the renderer works correctly when given a well-formed tree, independent of agent involvement.

### Iteration 4 — End-to-end DSL run on real concepts (2026-05-27 PM)

**What we ran.** Two visualizer subagent invocations in parallel:

- **Run 1:** `GIB markov-representation --dsl` (expected: agent picks `Decompose` cleanly for a factorization).
- **Run 3:** `GIB gib-cat-sampling-worked --dsl` (expected: agent refuses, falls back to graphviz, names the missing operator).

**What it produced.**

- Run 1 produced `markov-representation.dsl.png` in the vault. The agent picked the operator tree `Decompose(Decompose)` matching the algebraic structure. The picture rendered correctly per the DSL's spatial semantics, but **read as algebra, not as a Markov chain.** The user's response: "I don't see any improvement at all. especially markov rep, which part of it looks like a markov chain concept?!"

- Run 3 produced the refuse-and-name result described above, but the graphviz fallback PNG (`gib_cat_sampling_worked.png`) **still contained numerical tuples in labels** despite the agent claiming the self-check passed. Either the agent didn't run the check, or it rationalized that worked-example coordinates were "named values" not "numerical values."

**Why we stopped.** Two converging signals:

1. The user judgment was unambiguous: "I don't see any improvement at all." After four iterations.
2. Even where the agent did the right *structural* thing (Run 3's honest refusal), the *output quality* of the fallback path was worse than the previous attempt because the rules didn't bite.

The Run-1 output is the cleanest evidence that the architecture has hit a ceiling: the agent identified the entities, picked a defensible operator tree, ran the renderer, and produced a picture that — while structurally correct — does not resemble what a human would draw for the same concept.

## What we learned (preserve these for the side project)

1. **Dictionary-as-style-guide works.** Mapping `dict_id → (shape, palette, glyph)` rather than `dict_id → pasted PNG` produces visually coherent atoms at any scale. The 23 entities + 12 relations + 37 actions in `DICTIONARY.md` survived four backend changes without modification. Keep this framing in the side project.

2. **Editorial constraint outperforms prompt elaboration.** The cast ≤ 6 rule produced a measurable reduction in over-enumeration. The label discipline rule transferred between skills. Both were small constraints that the agent honored. *Verbose prompt instructions did not produce comparable behavior change.* Future work should bias toward constraints over instructions.

3. **The agent will refuse honestly when given a way out.** Run 3's "this needs a Pipeline operator" was a real result. Any future DSL must always include a structured "stop and report" exit; the agent will use it when the structure genuinely doesn't fit.

4. **Self-checks don't bite unless they're mechanical.** The agent claimed in its Run-3 report that the no-numerical-values check passed, but the labels still contained `(0.54, 0.24, 0.15, 0.07)`. Self-checks that depend on the agent's judgment (interpret "numerical values" liberally) fail. Self-checks that are regex-or-validator (in `_validate()`) fire reliably. Bias the side project toward mechanical checks.

5. **Operator-tree DSLs are the right shape, but the operator set must be derived from the corpus.** Algebra-shaped operators (`Juxtapose`, `Decompose`) are a minority idiom. Sequence-shaped operators (`Pipeline`, `Branch`, `Merge`, `Plate`) are the majority. Don't pick operators speculatively; derive them from a labeled corpus.

6. **The LLM can identify entities and verbs reliably; it cannot make global spatial decisions.** Every iteration confirmed this. The agent could always tell you which dictionary atoms were in the source text. It could not reliably tell you "this should be foreground, that should be inset, the loop frame goes around these three." That's the gap the side project must close.

## What we tried that didn't work (so don't redo it)

- **More verbose SKILL.md prompts.** Every iteration added more rules. Rules beyond a few key constraints become noise — the agent picks up the headline constraints and skims the rest.

- **Trusting agent-claimed self-checks.** Multiple runs reported "✓ no numerical values in labels" while emitting numerical values. Mechanical validation only.

- **Inferring spatial intent from text alone.** "The paper says factorizes, so use `Decompose`" is brittle: the same word can map to many spatial idioms (a brace, a chain of states, two side-by-side plates). The text → spatial mapping has to be learned, not pattern-matched.

- **Iterating on the operator vocabulary without a corpus.** Each new operator suggestion was motivated by one or two failures, which produces a vocabulary tuned to the most recent failure rather than the corpus.

- **AI image generation (DALL·E / SD).** Ruled out 2026-05-20 because faithful structural correspondence is unachievable. Still true.

## Side project — research spec

Frame this as **learning a layout policy**, not as prompt-engineering an LLM to emit picture specs. The LLM is good at extraction (entities, relations, intent); it is bad at spatial composition (foreground/background, plates, callouts, dataflow routing). The side project keeps the LLM for the part it's good at and replaces the part it's bad at with a learnable model.

### Problem statement

Given a structured intermediate representation produced by an LLM from paper text:

```text
{
  entities: [{id, type (dict_id), label, paper_intent}],
  relations: [{src, dst, type, label}],
  intent: <one of: dataflow | comparison | factorization | chain | landscape | ...>
}
```

produce a 2D figure spec:

```text
{
  shapes: [{id, glyph_kind, x, y, w, h}],
  arrows: [{src_id, dst_id, route, style}],
  frames: [{contains: [id*], style, label}],
  callouts: [{anchor: id, text, position}]
}
```

that is faithful to the input and visually matches the dominant idioms in a curated corpus of ML figures.

The split is intentional: LLM owns the *extraction* (right side of the arrow); a learned model owns the *layout* (right side of the arrow).

### Corpus

100–200 hand-labeled ML figures spanning the dominant kinds:

- Architecture diagrams (sequential + branching).
- Probabilistic graphical models (plates, observed/latent).
- Loss-and-objective diagrams (multi-branch with KL/MSE leaves).
- Algorithm trace figures (per-step state).
- Worked examples (input → intermediate → output with concrete instances).
- Geometric / manifold pictures.

Each labeled with: (a) the structured intermediate above, (b) the rendered figure spec, (c) the original paper figure as a reference.

This is the binding constraint. Without ≥ 100 labeled examples no model will converge, and the human-judgment loop we ran in PaperLab will repeat.

### Prior art to survey before coding

- **LayoutDM, LayoutDiffusion** — diffusion-based discrete layout generation. Closest to "given a set of typed boxes, place them on a canvas."
- **DiagrammerGPT, Sketch2Code, Pix2Struct** — recent LLM + diagram work; mostly UI / flowcharts; relevant for the LLM-side extraction pattern.
- **Constraint-based layout solvers** (Cassowary, Z3-based UI layout, the OPTUNA / OR-tools constraint kits). A learned policy can be a *prior* on a constraint solver rather than a black box — gives interpretable controllability.
- **Plate diagram synthesis** — the PGM literature has small bespoke tools (Daphne / GraphViz-PGM); these encode plate semantics directly and may inform the operator vocabulary.
- **Mermaid, D2, TikZ-CD** — declarative diagram languages already encode some of the operators a learned model would output. Worth a structural comparison: what operators do they have, which are missing, which are vestigial.
- **Sketch-RNN, IconNet** — older but relevant; produced glyph drawings from concept tokens.

The first month of the side project should be a literature survey, not code.

### Model directions to consider

In rough order of complexity:

1. **Rule-based renderer with learned operator picker.** Keep the symbolic renderer (the `tools/render_dsl.py` skeleton is fine). Replace the LLM operator-picking step with a small classifier trained on `(intermediate, paper_intent) → operator_tree`. Cheap; testable against the labeled corpus.

2. **Constraint-based layout with a learned prior.** The model emits soft constraints (`prefer_above(A, B)`, `align_horizontally(A, B, C)`, `inside_plate(plate_l, [A, B, C])`) that a solver realizes. Learned from corpus annotations. Interpretable; failures are debuggable.

3. **End-to-end neural layout.** A graph-to-image or graph-to-spec model (graph transformer encoder, layout decoder). Most expressive but least debuggable; needs the most data.

Option 1 is the right first step. It tests whether the corpus is large enough to drive any model, before committing to architectures.

### Evaluation

Three measures, in order of importance:

1. **Structural faithfulness.** Does the output spec preserve every entity and relation in the input? Mechanical check.
2. **Human-judgment quality.** Side-by-side with the reference figure, does a human (the user, ideally several) say "this looks like the same kind of figure"? Rubric: same intent classification (chain / comparison / plate / ...), same set of plates and callouts, same coarse spatial arrangement.
3. **Diagram literacy.** Can a reader who has not seen the source paper restate the figure's claim from the rendered output? Stronger than (2) and the bar we never reached in PaperLab.

### Baselines to beat

- **Graphviz auto-layout** with the dictionary palette (iteration 1 of this work).
- **Operator-tree DSL with LLM operator-picking** (iteration 3 of this work).
- **Pure LLM picture-spec emission** (no rendering layer; LLM emits SVG or TikZ directly).

These three are the things the side project must beat. They are also the things this repo already produces, which makes them cheap baselines to wire in.

### What the side project should NOT do

- **Replace the LLM entirely.** The extraction half is genuinely good; only the layout half is bad. A model that re-does extraction will be a worse extractor.
- **Aim for hand-drawn quality on day one.** The realistic v1 is "structurally faithful and recognizable as the right kind of figure." Beauty is later.
- **Skip the corpus.** No corpus, no project. If the corpus is the blocker for six months, that's the project for six months.
- **Build inside PaperLab.** PaperLab is a tooling project; this is a research project. Different cadence, different success criteria. Repo-separate.

### Suggested first milestone

A 4-week sprint:

- Week 1: literature survey (LayoutDM, DiagrammerGPT, constraint-based layout). Write a 5-page state-of-the-art note.
- Week 2: hand-label 30 figures (smallest viable corpus). Define the intermediate representation rigorously.
- Week 3: implement Option 1 (rule-based renderer + learned operator picker). Reuse `tools/render_dsl.py` skeleton.
- Week 4: evaluate against the three baselines. Decide whether to continue (extend corpus, try Option 2) or to write up the negative result and stop.

The decision point at end of week 4 is genuine. If the labeled corpus is too small to drive even Option 1, that is a data-collection project and a research-direction shift, not a "try harder" moment.

## Artifacts retained in this repo

Even though the agent is on hold, the following artifacts are kept because they're useful inputs for the side project:

- `tools/visualize_concept.py` — graphviz pipeline (1000 lines; mature dictionary palette).
- `tools/figure_dsl.py` + `tools/render_dsl.py` — operator-tree DSL skeleton (matplotlib renderer; reusable as the symbolic backend for Option 1 above).
- `.cursor/skills/ml-visualization/SKILL.md` + `DICTIONARY.md` + `DICTIONARY.pdf` + `symbols/` — the dictionary itself. This is the most reusable single asset; ~70 typed visual idioms with worked examples.
- `.cursor/skills/ml-visualization-dsl/SKILL.md` — operator-picking decision tree and label discipline rules. Reusable as the prompt for the LLM-side extractor in the side project.
- `sandbox/dsl_reference.png`, `sandbox/stress_a.png`, `b.png`, `c.png` — renderer correctness evidence; reuse as smoke tests when the renderer is forked into the side project.
- `sandbox/GIB/v3_panel_b.png` — last graphviz reference output; one of the labeled-corpus seeds.
- `.cursor/agents/visualizer.md` — agent prompt with both graphviz and DSL paths documented.

## Artifacts to consider retiring (not now, but at next cleanup)

- `sandbox/GIB/dry_run_*.py` and `sandbox/GIB/dry-run-*.png` — exploratory scripts from iteration 1; superseded by the documented pipelines.
- Vault outputs `markov-representation.dsl.png` + `.yaml` and `gib_cat_sampling_worked.png` + spec — these are the artifacts the user reviewed and rejected; they document the failure but aren't useful as-is. Move to a `sandbox/visualizer-postmortem-figures/` directory or delete after the side project gets started.

## Closing note

Two facts that should travel with this document:

- The user's instinct that this was an under-modeled problem proved correct. The architectural pivots all kept the model in the loop and only changed the framing; none addressed the underlying spatial-composition gap.
- The work was not wasted. The dictionary, the editorial-constraint pattern, the DSL skeleton, and the refuse-and-name behavior are all reusable inputs to the side project. The negative result is *more useful* with these in hand than without them.
