---
name: ml-explanation
description: Defines the schema for writing single-concept math explanations from ML papers. Concept files live at `vault_path(slug, "<concept>.md")`. Use when explaining a concept from a paper, clarifying paper math, or writing a concept file.
---

# ML Explanation Schema

## Purpose

This file defines the schema for single-concept explanation files. As of 2026-05-27, two different agents write files conforming to this schema, with two different filenames and slightly different responsibilities:

| Writer | Output filename | Audience | Cross-references |
|---|---|---|---|
| **Explainer** (backend, invoked by Tutor) | `<concept>-<slug>.md` | Tutor (intermediate artifact); user may also read | One-way Section 6 links allowed; Explainer does not maintain reciprocal links |
| **Tutor** (user-facing) | `<concept>.md` | User (final study reference) | Must maintain **bidirectional** links per `ml-tutor/SKILL.md` rule R7 |

The on-disk schema (six sections, math conventions, notation rules) is the same for both files. The only differences are the filename, the writer, and whether bidirectional cross-references are maintained.

The user does not invoke the Explainer directly — all concept work flows through the Tutor (`/tutor <slug>`). See `.cursor/skills/ml-tutor/SKILL.md` for the full Tutor protocol.

## Conventions
Global rules that apply to all sections:

- **audience**: PhD statistician (probability, linear algebra, optimization fluent; not DL/causal jargon)
- **invocation**: Concept on demand
- **sources**: spec.md first; PDF if needed; external knowledge freely
- **length target**: 1- 2 pages
- **math notation conventions**: use LaTeX between `$ ... $` (inline) and `$$ ... $$` (display). Never use Unicode math. Never use `\( ... \)` or `\[ ... \]` — they don't render in GitHub markdown preview. Match the paper's notation; derive when the derivation itself is the unfamiliar part.
- **notation**: when the paper defines a symbol for a concept, use the paper's
  notation throughout the explanation file — not a textbook version or
  alternative convention. Notation must be internally consistent across
  all six sections: if Section 1 introduces $U' \subseteq \mathcal{V}$ for
  the intervention set, Sections 2-6 use the same symbol. If the paper
  uses notation that conflicts with a more common textbook convention,
  note the alternative once in the Definition section (e.g., "$U'$ in this
  paper corresponds to what Pearl (2009) writes as $X$") but then use the
  paper's notation consistently thereafter.
- **output file naming**:
  - When written by the **Explainer** (backend), the file is named `<concept>-<slug>.md`. The `-<slug>` suffix marks it as paper-bound backend output.
  - When written by the **Tutor** (user-facing), the file is named `<concept>.md` (no slug suffix). The Tutor composes this file from the Explainer's `<concept>-<slug>.md` plus general field framing.
  - Either way, do NOT use an `explanation_` prefix.
- **diagram rules**: Mermaid for graphs/flows; ASCII for tensor shapes; reference paper figures when they exist. Use graphs/flows for concept explanation as necessary.
- **cross-reference syntax**: Plain markdown links.
- **structure**: 6 sections: Definition, Motivation, Intuition, Formal statement, Worked example, Cross-references.
- **file placement rule**:
  - Explainer writes to `vault_path(slug, "<concept>-<slug>.md")`, where `<slug>` is the paper the Tutor invoked the Explainer for. Paths are resolved via `tools/paths.py`.
  - Tutor writes to `vault_path(slug, "<concept>.md")`, where `<slug>` is the paper of the Tutor session that produced the file. If the same concept later comes up in another paper's session, the Tutor reads the existing `<concept>.md` from the originating paper's folder rather than creating a duplicate; per-paper differences may be noted in the new paper's `tutor_notes.md`.
- **Bidirectional cross-referencing**:
  - **Tutor (`<concept>.md` writes only)** must maintain bidirectional links: when Section 6 of a new `<concept>.md` links to another `<concept>.md` in any vault paper folder, the Tutor must add a reciprocal link to that file's Section 6. Procedure:
    - Read the target file's Section 6 ("Related concepts" sublist).
    - If it currently says "None.", replace that entire line with a new bulleted list containing the reciprocal link.
    - If it already has a "Related concepts" list, append the new link as a new bullet. Do not modify, reorder, or remove existing entries.
    - Each bullet:  `[<concept>](<concept>.md) — one-sentence description of the relationship`.
    - The invariant: if file A's Section 6 links to file B, then file B's Section 6 must link back to A.
  - **Explainer (`<concept>-<slug>.md` writes)** does NOT maintain bidirectional links. The Explainer may include one-way Section 6 cross-references where they help the reader; the Tutor reconciles cross-references when composing the final `<concept>.md`.
- **Vault-wide existing-file check**: the Tutor (not the Explainer) checks `vault_root()/*/<concept>.md` paths before writing. If a concept already has a `<concept>.md` somewhere in the vault, the Tutor reuses the existing file rather than creating a duplicate. Per the rule above, this lookup is the Tutor's responsibility; the Explainer's backend file (`<concept>-<slug>.md`) is always written fresh per paper.

## Required sections (in this order)

### 0. Header

Every `<concept>.md` must begin with a header in this format:

```markdown
---
paper: <slug>
category: model
agent: tutor       # or `agent: explainer` for the `<concept>-<slug>.md` backend intermediate
tags:
- AI-guided-paper-reading
- concept-explanation
---

# <concept>
**Paper context:** one-sentence summary of what the paper does

---
```

### 1. Definition
One or two sentences stating what the concept is. Name it, place it in its mathematical category (e.g., 'a regularization term', 'an attention mechanism', 'a graph operation'), and give its defining property. No motivation, no derivation — just identification.

for example:
Graph mutilation is a graph operation that removes all edges incoming to a specified set of nodes, producing a modified graph in which those nodes have no parents. It is the graph-level implementation of the do-operator in Pearl's structural causal models.

### 2. Motivation

One or two paragraphs answering: why was this concept introduced? What problem does it solve? What would go wrong — mathematically or practically — without it? If the concept originated outside the paper, briefly note its history; if it's specific to the paper, explain the paper's motivation.

for example:
In a structural causal model, each node's value is determined by its parents through a structural equation. When we *intervene* on a node — forcing it to a specific value regardless of its usual causes — the original structural equation for that node is overridden. Mutilation captures this mathematically: by removing incoming edges to the intervened node, we sever its dependence on its parents, while leaving its downstream effects (outgoing edges) intact. Without mutilation, a causal model would conflate observing a variable (conditioning) with setting it (intervening), and predictions about interventions would be wrong. In PDGrapher specifically, mutilation is how a candidate therapeutic perturbagen $U'$ is "applied" to the proxy causal graph before running message passing — the graph fed into the GNN is $G^{U'}$
, not $G$.

### 3. Intuition

One paragraph describing what kind of thing is this. It describes a mental picture or metaphor before you see the math. It's pre-formalization. Intuition is pre-formal — a metaphor, geometric picture, or mental model that prepares the reader for the math. It should not use specific numbers (that's Section 5's job). If you reach for a concrete example, step back and describe the shape of the thing instead.

for example:
Think of a causal graph as plumbing. Each edge is a pipe carrying influence from upstream genes to downstream ones. Normally, a gene's state is whatever flows into it through its incoming pipes. When you intervene on a gene — forcing it to a particular value with a drug or CRISPR edit — its state is now externally set, so what the upstream pipes "wanted" to deliver no longer matters. Mutilation is cutting those incoming pipes. The outgoing pipes stay connected, because the gene's new externally-set value still propagates downstream. Geometrically: a mutilated node becomes a root of its connected component, a source with no history.

### 4. Formal statement
Text and/or bullet point or tables as necessary to formally state the mathematical concept. Use math notations that correspond to the concept in the paper.

When the paper's original formulas are the clearest statement of the concept, reproduce them directly (with equation numbers when referenced in spec.md). Use the paper's notation, matching the symbols introduced in Sections 1-3 of this file.

When a formula is directly taken from the paper and the paper numbers it, include the paper's equation number in parentheses after the formula, e.g., \tag{Eq. 3}

If the paper's notation is ambiguous (the same symbol is used for two different things, or different symbols are used for the same thing), resolve the ambiguity locally by picking the most consistent interpretation, and note the ambiguity in the Definition section with a ⚠️ prefix.

for example:

Let $G = (\mathcal{V}, \mathcal{E})$ be a directed graph with nodes $\mathcal{V}$ and edges $\mathcal{E} \subseteq \mathcal{V} \times \mathcal{V}$. For an intervention set $U' \subseteq \mathcal{V}$, the **mutilated graph** is:

$$G^{U'} = (\mathcal{V}, \mathcal{E}^{U'})$$

where

$$\mathcal{E}^{U'} = \mathcal{E} \setminus \{(u, v) \in \mathcal{E} \mid v \in U'\}.$$

In words: remove every edge whose *target* lies in $U'$. Outgoing edges from $U'$ and all edges not touching $U'$ are preserved.

Under the causal Markov condition and no unobserved confounders, the interventional distribution on the mutilated graph equals the observational conditional distribution on it:

$$P^{G^{U'}}(\mathbf{V} = \mathbf{x}^t \mid \text{do}(U')) = \prod_j P\!\left(v_j = x_j^t \mid \mathbf{Pa}_{v_j}^{G^{U'}}\right),$$

where $\mathbf{Pa}_{v_j}^{G^{U'}}$ denotes the parent set of $v_j$ in the *mutilated* graph. For $v_j \in U'$, the parent set is empty, so the factor reduces to the marginal $P(v_j = x_j^t)$ — i.e., the intervention sets the value directly.

### 5. Worked example
A small, concrete instance (typically 3-5 items: 3 genes, 2 cells, 4 nodes). Execute the math step-by-step on specific numbers. Show inputs, intermediate values, and output. The whole example should fit on a screen.

for example:

Consider a 4-gene graph with edges $A \to B$, $B \to C$, $B \to D$. The adjacency matrix is:

```
     A  B  C  D
  A [ 0  1  0  0 ]
  B [ 0  0  1  1 ]
  C [ 0  0  0  0 ]
  D [ 0  0  0  0 ]
```

Suppose we intervene on $B$: $U' = \{B\}$.

**Step 1 — Identify edges incoming to $U'$.** The edges whose *target* is in $\{B\}$: $\{A \to B\}$.

**Step 2 — Remove them.** Zero out the $A \to B$ entry:

```
     A  B  C  D
  A [ 0  0  0  0 ]  ← A→B removed
  B [ 0  0  1  1 ]  ← B→C, B→D kept
  C [ 0  0  0  0 ]
  D [ 0  0  0  0 ]
```

**Step 3 — Interpret.** In $G^{U'}$, node $B$ has no parents. Its value $x_B^t$ is set by the intervention. $A$ still has its original structural equation, but it no longer affects $B$. $C$ and $D$ inherit the intervened value of $B$ through the preserved outgoing edges.

**Step 4 — Factor the joint.** The interventional joint becomes:

$$P^{G^{U'}}(A, B, C, D \mid \text{do}(B = x_B^t)) = P(A) \cdot \mathbb{1}[B = x_B^t] \cdot P(C \mid B) \cdot P(D \mid B).$$

Compare to the observational joint $P(A) \cdot P(B \mid A) \cdot P(C \mid B) \cdot P(D \mid B)$: the $P(B \mid A)$ factor has been replaced by the intervention indicator. This is the formal meaning of "cutting the incoming pipes."

### 6. Cross-references
Include only links that genuinely help the reader. If there are no meaningful cross-references at the time of writing, write 'None.' Do not write 'None yet' — the bidirectional-link rule ensures this line is updated automatically when a related file is created later.

When linking to a heading within another markdown file, derive the anchor from the heading text: lowercase, replace spaces with hyphens, strip punctuation (., ,, :), and preserve any double-hyphens produced by punctuation-plus-space sequences like /. Example: heading ## 3. Problem setup / Objective → anchor #3-problem-setup--objective.


for example:

**Related concepts:**
- [do-calculus](do-calculus.md) — the formal framework that defines intervention via mutilation
- [causal Markov condition](causal-markov-condition.md) — the assumption that licenses the factorization in Section 4

**Places in spec.md:**
- [spec.md §3](spec.md#3-problem-setup--objective) — where $G^U$ first appears in PDGrapher's problem formulation
- [spec.md §6.1](spec.md#61-training) — where mutilation is applied before each GNN forward pass

**External references:**
- Pearl (2009), *Causality: Models, Reasoning, and Inference*, Chapter 3 — the canonical treatment of do-calculus and mutilation
