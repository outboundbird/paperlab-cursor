# PaperLab Roadmap

Status as of 2026-05-18. Living document.

## Planned units

Each entry is a capability we've agreed to build, mapped to the right Cursor primitive (subagent / skill / rule / hook / MCP). Build order is top-to-bottom; revisit after each unit ships.

### 1. `visualizer` subagent + `ml-visualization` skill

- **What:** Turns `spec.md`, `<concept>.md`, and `code_map.md` into visual artifacts — diagrams, flowcharts, slide decks — to support visual learning.
- **Primary outputs:** Mermaid diagrams (inline in markdown) and Marp slide decks (`papers/<slug>/slides.md`). Both render natively in GitHub and Obsidian.
- **Fallback outputs when Mermaid/Marp are inadequate:**
  - matplotlib / PIL figures saved as PNG/SVG for numerical plots or precise geometry
  - TikZ for publication-quality math diagrams
  - tldraw canvases (via the `tldraw` MCP already configured) for architectural sketches
- **Why subagent + skill:** Choosing *what* to visualize needs judgment (subagent); diagram conventions and format-selection rules are reusable reference material (skill).
- **First test case:** Memento paper — visualize the MDP from `papers/Memento/mdp.md` and the algorithm framework from `papers/Memento/spec.md`.
- **Acceptance:** produces at least one Mermaid diagram + a Marp deck summarizing the paper's algorithm with diagrams, not just bullet points rephrasing `spec.md`.

### 2. `tutor` subagent + `ml-socratic` skill

- **What:** Interactive, multi-turn teacher. Reads `spec.md` + concept files, asks what the user knows, picks next concept, explains with visuals (delegates to `visualizer` when useful), quizzes, adapts.
- **State:** Writes `papers/<slug>/tutor_log.md` so progress persists across sessions.
- **Why subagent + skill:** Adaptive multi-turn dialogue needs judgment; Socratic patterns and quiz templates are reference (skill).

### 3. Obsidian integration

- **Hook:** post-write hook that syncs new/changed `papers/<slug>/*.md` and `comparisons/*.md` into the user's Obsidian vault, rewriting links to `[[wikilinks]]` where appropriate.
- **Rule:** `obsidian-compatible-markdown.mdc` — enforces wikilink-friendly, GitHub-compatible markdown (no exclusive-to-one-renderer syntax).
- **Open question:** vault path; one-way (paperlab → vault) vs. two-way sync.

### 4. `prerequisite` subagent + `ml-prerequisites` skill

- **What:** Scans `spec.md`, identifies assumed background concepts, checks existing `papers/*/` and the Obsidian vault for coverage, produces a prerequisite graph + primers for gaps.
- **Why subagent + skill:** Detecting assumed knowledge needs judgment; the prereq-graph schema is reference.

### 5. `comparator` subagent + `ml-comparison` skill

- **What:** Cross-paper synthesis. Inputs: N paper slugs + a comparison axis (e.g., "GIB objective formulation"). Output: `comparisons/<topic>/comparison.md` with a comparison table and a synthesis narrative.
- **Why subagent + skill:** Synthesis is judgment-heavy; the comparison-doc schema is reference.
- **New top-level folder:** `comparisons/`.

### 6. `experimenter` subagent + `ml-sandbox` skill

- **What:** Generates a minimal toy implementation in `sandbox/<paper-slug>/` with a small synthetic or standard dataset, enabling A/B comparison of methods across papers. Pairs with `comparator`.
- **Why subagent + skill:** Experiment design is judgment-heavy; toy-experiment scaffolding patterns are reference.

### 7. External-data access

- **MCP:** start by reusing `firecrawl` (already configured). Add a thin `arxiv` MCP only if structured metadata becomes a recurring need.
- **Rule:** `external-fetch-budget.mdc` — max 5 external fetches per concept; prefer arXiv abstract + 1 blog + author page; never crawl whole sites.

## Decision framework: agent vs. skill vs. rule vs. hook vs. MCP

Recorded here so future-us doesn't re-derive it.

1. Needs access outside the repo? → **MCP**
2. Runs automatically on events? → **Hook**
3. Is a *role* with judgment? → **Subagent** (typically uses skills + MCPs)
4. Is *reference material* for specific tasks? → **Skill**
5. Is an always-on (or glob-scoped) *constraint*? → **Rule**

Litmus tests:

- Skill vs. Rule: needed *sometimes* (skill) or *always when touching matching files* (rule)?
- Skill vs. Subagent: *how to do it* (skill) vs. *thing that does it* (subagent)?
- Subagent vs. Hook: needs *judgment* (subagent) vs. *deterministic reaction* (hook)?
- MCP vs. nothing: a shell + `Read` won't cut it? → MCP.

Anti-pattern: building a subagent for a deterministic transformation. Use a hook or script.

## Deferred features

_(template preserved — fill in as we defer things)_

## Known limitations

_(template preserved)_

## Schema improvement candidates

_(template preserved)_

## Reference: what's currently working

- Subagents: `acquirer`, `dissector`, `implementer`, `explainer`, `critic`
- Skills: `ml-acquisition`, `ml-paper-spec`, `ml-code-map` (+ `DEEP_DIVE`), `ml-explanation`, `ml-synthesis`, `ml-critique`
- Papers acquired: `Memento` (with `spec.md`, `mdp.md`)