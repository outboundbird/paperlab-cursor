# PaperLab: Agent-Assisted Reading Of ML Methods Papers

PaperLab helps the user understand mathematics in machine learning and deep learning papers.

## YAML front-matter

Every agent-generated markdown file under `<vault>/<slug>/` carries a YAML front-matter with these keys in this order:

- `paper: <slug>` — groups all files for one paper.
- `category:` — broad bucket (`model`, `tutor`, ...).
- `agent: <name>` — identifies the subagent that wrote the file. Required as of 2026-05-28 for the post-hoc verifier hook to know which writer's output to verify. Allowed values: `acquirer`, `dissector`, `implementer`, `critic`, `tutor`, `explainer`, `comparator`, `experimenter`. The hook compares against this set; files without `agent:` (legacy vault content) are skipped silently.
- `status:` — the lifecycle step this artifact represents. Per-paper pipeline values, in order: `acquired`, `dissected`, `implemented`, `critiqued`, `tutored`. `blueprinted` is a side-branch of `implemented`: it marks `code_blueprint.md`, the from-math reconstruction the `implementer` writes when a paper has **no official code** (vs. `implemented` for `code_map.md`, which maps real upstream code). Multi-paper experiment-suite artifacts sit outside the linear per-paper pipeline: `compared` (the `comparator`'s `comparison.md`), `designed` (the `experimenter`'s `design.md`), and `evaluated` (the `experimenter`'s `findings.md`). Records where the work is in the workflow so the lifecycle becomes queryable (see "Graph index groundwork" below).
- `sources:` — list of `[[wiki-links]]` to the artifacts or papers this file was derived from (provenance edges). Example: a `comparison.md` lists the `spec.md` files it read. Omit or leave empty for root artifacts (e.g. `paper-info.md`).
- `concepts:` — list of `[[wiki-links]]` to canonical concept names this artifact touches (concept edges; the cross-paper connective tissue). Names come from the shared concept vocabulary (see "Graph index groundwork").
- `tags:` — Obsidian tags.

**Multi-paper variant (experimenter suite).** Files under `<vault>/experiments/<topic>/` span several papers, so they replace the singular `paper:` key with `topic: <topic>` and a `papers:` list of slugs. Example header keys, in order: `topic:`, `papers:` (list), `category:` (e.g. `comparison`), `agent:` (e.g. `comparator`), `status:`, `sources:`, `concepts:`, `tags:`. These files are verified by the comparator's **inline** gate, not the post-hoc hook (the hook skips the `experiments/` tree — see Verifier system).

### Graph index groundwork

`status:`, `sources:`, and `concepts:` are **infrastructure for a future graph index** (`reindex.py`, see `ROADMAP.md`). They are inert today — no tool reads them yet — but agents populate them now so the data exists across the vault when the reader is built. Until then they double as Obsidian backlinks/graph-view edges, which work immediately.

- **`status` vocabulary** is the linear per-paper pipeline plus `tutored`, with `compared` for multi-paper artifacts. Use the value that matches the artifact's role (e.g. `spec.md` → `dissected`, `code_map.md` → `implemented`, `critic_reviews.md` → `critiqued`, tutor/explainer files → `tutored`, `comparison.md` → `compared`).
- **`sources` and `concepts` use `[[wiki-link]]` syntax** so Obsidian renders the relationships with zero tooling. `sources` links point to other artifacts (e.g. `[[GIB/spec.md]]`); `concepts` links point to canonical concept names (e.g. `[[information-bottleneck]]`).
- **Concept vocabulary** is **grown on demand**, not pre-seeded: agents append new canonical names to the shared list at `.cursor/skills/concept-vocabulary.md` as they encounter concepts, reusing an existing name when one fits rather than coining a variant (avoid `IB` vs. `Information Bottleneck` drift). Match against the existing list before adding.
- **These keys are prose-enforced** until `reindex.py` validates them, so partial adoption across legacy files is expected; a backfill pass over existing papers is a known follow-up.

The slug is **verbatim user input** — never normalize, capitalize, or pluralize. If the slug contains any of `:`, `#`, `[`, `]`, `{`, `}`, `,`, `&`, `*`, `!`, `|`, `>`, `'`, `"`, `%`, `@`, `` ` ``, or starts with whitespace or `-`, wrap it in double quotes: `paper: "weird:slug"`. The `paper:` key lets Obsidian Dataview / property search group every file (spec.md, code_map.md, tutor_log.md, concept files, ...) for one paper.

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
- `sandbox/<slug>/` — per-paper toy experiments (git-ignored).
- `sandbox/experiments/<topic>/` — multi-paper comparison experiments for the `experimenter` suite. Code + seeds are tracked; generated `data/` is git-ignored. Resolve via `repo_experiments_dir(topic)`. `<topic>` is a user-chosen problem class, not a paper slug.
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

The `experimenter` suite (see Cursor Subagents) writes outside the per-paper folders, under `<vault_paperlab_path>/experiments/<topic>/` (resolve via `vault_experiments_dir(topic)`):

- `design.md` — experiment design: topic, criterion, method set, data-synthesis design, rationale.
- `findings.md` — results write-up.
- `comparison.md` — standalone conceptual comparison from the `comparator` (filename to be finalized in the build phase).

> The `visualizer` subagent is now an **independent project**, exported out of PaperLab; see [`visualizer-todo.md`](./visualizer-todo.md) and the archive branch `visualizer`.

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

### Learning suite

The five per-paper agents that take one paper from acquisition through understanding form the **Learning suite** (`acquirer`, `dissector`, `implementer`, `critic`, `tutor`, plus the backend `explainer`). They share the per-paper `status` lifecycle (`acquired → dissected → implemented → critiqued → tutored`) and write to `<vault>/<slug>/`. This is the counterpart to the multi-paper Experimenter suite below.

- `acquirer` sets up the per-paper repo folder (`papers/<slug>/`) and vault folder (`<vault>/<slug>/`), downloads PDFs/supplements, clones upstream repos, and writes `paper-info.md` to the vault.
- `dissector` reads the paper PDF and writes `spec.md` to the vault.
- `implementer` maps paper concepts to a concrete implementation and writes `code_map.md` to the vault; deep-dive mode writes `code_map__<slug>__<component>.md`. The mapped code is **one of two sources** (one `code_map.md` schema for both — see `ml-code-map`): `official` (`repo_upstream_dir(slug)`) or `reconstructed` (the `coder`'s `vault_code_dir(slug)/method.py`, built from a blueprint when no official code exists). When mapping reconstructed code it re-derives the walkthrough from `spec.md` + `method.py`, **not** from its own blueprint (firewall). **Blueprint mode** (explicit, opt-in) handles papers with **no official code**: it reconstructs a framework-agnostic implementation contract from the paper's math and writes `code_blueprint.md` (`status: blueprinted`), gated **pre-emission** by the `critic` (draft passed as payload → retry ×2 → escalate; written only on PASS). See [`log/2026-06-03-implementer-coder-blueprint-design.md`](./log/2026-06-03-implementer-coder-blueprint-design.md) and [`log/2026-06-04-codemap-from-coder-critic-audit.md`](./log/2026-06-04-codemap-from-coder-critic-audit.md).
- `critic` audits claims, reproducibility, and paper-code alignment, then writes `critic_reviews.md` to the vault. The audit adapts to the `code_map.md` source (`ml-critique` "Audit source"): for `official` code it weighs author choices and upstream/dataset reproducibility; for `reconstructed` code it becomes a **fidelity audit** (does the coder's reconstruction drift from the paper's math?) with reconstruction-fidelity reproducibility rows — the firewalled **hop-2-vs-spec** check (the critic re-reads the spec independently to audit code it did not write). A backend **blueprint-check mode** (invoked by the `implementer`, never the user) audits a draft `code_blueprint.md` **pre-emission** against the critic's own independent reading of the paper's math, returning a PASS/FAIL verdict without writing a file (the **hop-1** guard). A backend **extraction-fidelity mode** (invoked by the `experimenter`, never the user) gates Stage-2 component surgery **pre-run**: Check A audits each `extracted.py` against its `code_map.md` source (per-paper hard gate), Check B audits the synthesized `scaffold.py` against the shared principle; PASS/FAIL, no file. All three gate modes are the firewalled generator/discriminator check from the two-memory design.
- `tutor` is the user-facing conversational agent for understanding the paper's concepts. Reads `spec.md` and related vault files, talks with the user, invokes the `explainer` in the background when paper-bound content is missing, and writes `tutor_log.md` (every turn), plus `tutor_notes.md` / `<concept>.md` / `synth__<a>__<b>.md` (only on explicit user request).
- `explainer` is **backend-only as of 2026-05-27**. Invoked by the `tutor`, never by the user. Writes paper-bound intermediates: `<concept>-<slug>.md` (single-concept) or `synth__<a>__<b>-<slug>.md` (synthesis).
- `latex-verifier` is a read-only backend subagent. Wraps `tools/verify_latex.py` (lexer v1). Invoked by `tutor` and `explainer` in the inline gate (R10 / § 3.5) and by the post-hoc hook on vault writes. Never invoked by the user directly under normal flow.
- `citation-verifier` is a read-only backend subagent. Wraps `tools/verify_citations.py` (arXiv API + Crossref API + firecrawl CLI fallback, with per-paper cache). Invoked by `tutor` and `explainer` in the inline gate (R11 / § 3.6, sequential after the LaTeX gate) and by the post-hoc hook. Never invoked by the user directly under normal flow.

### Experimenter suite (designed 2026-05-29)

A four-agent suite for **multi-paper empirical comparison** of methods addressing the same problem class. Design + rationale: [`log/2026-05-29-experimenter-design.md`](./log/2026-05-29-experimenter-design.md). The `comparator` is **shipped (2026-05-29)**; the `experimenter` **design phase is shipped (2026-06-02)** with the **Stage-2 coder hand-off wired (2026-06-04, minimal)**; the `coder`'s **Stage 1 and Stage 2 are both shipped (2026-06-04)**; `evaluator` is designed but not yet built.

- `comparator` (**shipped**) is **dual-mode** (user-facing + backend). Conceptual method comparison from each paper's `spec.md` (+ `code_map.md` / PDF when needed) along a user-chosen axis. Runs standalone ("compare methods for `<topic>`") or as a design-phase input invoked by the `experimenter`. May refine a vague axis via propose-and-confirm. Writes `comparison.md` to `<vault>/experiments/<topic>/`, **verified by an inline LaTeX + citation gate** (the post-hoc hook skips the `experiments/` tree). Carries the critic's `[A]`/`[B]` inference discipline (forbidden `[C]`).
- `experimenter` (**design phase shipped 2026-06-02; Stage-2 hand-off wired 2026-06-04**) is the user-facing **orchestrator**. Holds the interactive session; owns the experiment design and data-synthesis *decisions* including the **§2b comparison seam** (load-bearing for Stage-2 coding); discusses results. Invokes `comparator`, `coder`, and `evaluator`. Writes `design.md` / `findings.md` to `<vault>/experiments/<topic>/`. **Current scope:** full design phase (design ⇄ user, conceptual trade-offs via the `comparator`, optional critic advisory, the §2b seam, writing `design.md` with the inline LaTeX + citation gate), then invoke `coder` Stage 2 with the seam, route the critic extraction-fidelity gate + the Seam-B user-check, and run to **results emitted**. It writes no code itself; the full implement/run orchestration protocol is still being fleshed out, and `findings.md` awaits the `evaluator`. Invoked via `/experimenter <topic>`.
- `coder` is the only agent that writes **runnable code**, split into two stages (design: [`log/2026-06-03-two-stage-coder-design.md`](./log/2026-06-03-two-stage-coder-design.md)). It **spans both suites**: Stage 1 is a per-paper, user-invokable step that belongs with the Learning suite's output (it writes to `<vault>/<slug>/code/`), while Stage 2 is the backend component-surgery mode the Experimenter suite drives. It is documented here because its two stages are one agent. **Stage 1 (shipped 2026-06-04, user-invokable)** writes reusable, invariant-validated method code for one paper to `vault_code_dir(slug)` (`<vault>/<slug>/code/`: `method.py` + `test_invariants.py`), from the paper's `code_blueprint.md` (primary route, no official code) or a reimplementation of its mapped upstream code. It exposes a hybrid `Method` interface (paper-natural guts + one documented entry point + an I/O contract block) and runs the blueprint's §4 invariants as runtime assertions on synthetic input before declaring done — the **hop-2-vs-blueprint guard**. It does **not** write the algorithm↔code walkthrough: after Stage 1, the `implementer` maps `method.py` into `code_map.md` (the `reconstructed` source) and the `critic` audits it against the spec (hop-2-vs-spec) — keeping documentation/audit off the code's author. Invoke with `/coder code <slug>`. **Stage 2 (component surgery, shipped 2026-06-04, backend-only)** is **not** black-box wrapping: from the experiment's `design.md` §2b seam it synthesizes a shared scaffold (principle + task fixed, pluggable slot `Protocol`) and extracts each paper's divergent component into `repo_experiments_dir(topic)/methods/<slug>/extracted.py` via the borrow ladder (import-direct / extract-and-refactor), preserving the source computation. Gated by the `critic`'s extraction-fidelity audit (Check A: each `extracted.py` vs. `code_map.md`, per-paper hard gate; Check B: `scaffold.py` vs. the shared principle) plus opportunistic coder-run behavioral equivalence. Invoked by the `experimenter`, not the user. The kickoff wrapping framing ([`log/2026-06-04-stage2-coder-adapt-kickoff.md`](./log/2026-06-04-stage2-coder-adapt-kickoff.md)) is superseded by the component-surgery redesign ([`log/2026-06-04-stage2-regime2-component-surgery-design.md`](./log/2026-06-04-stage2-regime2-component-surgery-design.md)).
- `evaluator` (designed) is **backend-only**. Interprets empirical run outputs and communicates only through the `experimenter`.

The interaction model is **Model 3 (hybrid)**: the `coder` does the heavy scaffold one-shot; the `experimenter` does the tight write→check→tweak loop in-session — mirroring the `tutor`/`explainer` split. The coder's two-stage split mirrors the same firewall philosophy: paper-bound method code lives with the paper (Stage 1, the vault), experiment glue lives with the experiment (Stage 2, the sandbox).

## Agent-To-Skill Mapping

Each subagent must read its corresponding skill before task-specific work:

- `acquirer` → `.cursor/skills/ml-acquisition/SKILL.md`
- `dissector` → `.cursor/skills/ml-paper-spec/SKILL.md`
- `implementer` general mode → `.cursor/skills/ml-code-map/SKILL.md`
- `implementer` deep-dive mode → `.cursor/skills/ml-code-map/DEEP_DIVE.md`
- `implementer` blueprint mode → `.cursor/skills/ml-blueprint/SKILL.md`
- `critic` → `.cursor/skills/ml-critique/SKILL.md`
- `tutor` → `.cursor/skills/ml-tutor/SKILL.md` (also reads `ml-explanation/SKILL.md` and `ml-synthesis/SKILL.md` before writing `<concept>.md` or `synth__<a>__<b>.md`)
- `explainer` single-concept mode → `.cursor/skills/ml-explanation/SKILL.md`
- `explainer` synthesis mode → `.cursor/skills/ml-synthesis/SKILL.md`
- `latex-verifier` → `.cursor/skills/ml-latex-verify/SKILL.md`
- `citation-verifier` → `.cursor/skills/ml-citation-verify/SKILL.md`
- `comparator` → `.cursor/skills/ml-comparison/SKILL.md`

Experimenter suite:

- `experimenter` → `.cursor/skills/ml-experiment-design/SKILL.md` (**shipped 2026-06-02**)
- `coder` → `.cursor/skills/ml-experiment-code/SKILL.md` (**Stage-1 and Stage-2 sections both shipped 2026-06-04**)
- `evaluator` → `.cursor/skills/ml-evaluation/SKILL.md` (planned, not yet written)

Treat those skills as authoritative for output structure, naming, scope boundaries, and self-checks.

## Verifier system

PaperLab runs two verifier subagents — `latex-verifier` and
`citation-verifier` — against agent-generated content to catch the
failure modes the Tutor and Explainer have produced in practice
(broken math blocks, hallucinated arXiv IDs, mismatched citation
metadata). Both verifiers are wrappers around pure-Python tools and
emit structured JSON; the subagents translate that into a
verdict-line report (`**PASS**` / `**FAIL**`) the calling agent
acts on.

### Two trigger paths

1. **Inline gate (Tutor, Explainer, Dissector, Comparator) — primary
   path.** Runs *before* emission / before declaring output complete.
   LaTeX first, citations second, with **separate retry budgets**
   (max 2 each). The Tutor's gate is the reference spec
   (`ml-tutor/SKILL.md` § R10 / R11); the Dissector gates `spec.md`
   (LaTeX only via the post-hoc hook for citations) and the Comparator
   gates `comparison.md` (both, since the post-hoc hook skips its
   `experiments/` tree).
   Outcomes are logged per-row in `tutor_log.md` (Tutor) or returned
   via the report-back to the Tutor (Explainer). Failed citations
   only fail the gate when `mismatched`; `unresolved` warnings are
   reported via a disclosure block but do not block emission, because
   transient resolver issues (proxy, rate limit, quota) commonly
   affect valid citations.
2. **Post-hoc hook — backstop for non-gated agents.** When any agent
   other than `tutor` or `explainer-intermediate` writes a `.md`
   file under a per-paper `<slug>/` vault folder, `.cursor/hooks.json`
   fires `tools/hooks/verify_on_vault_write.py`. The hook skips the
   `experiments/<topic>/` tree (multi-paper files have no single
   `<slug>` and are gated inline by the comparator). The hook runs both
   verifiers sequentially on the saved file, appends two blocks
   (one per verifier) to `vault_path(slug, "verifier_log.md")`, and
   returns a combined `additional_context` message so the calling
   agent sees the result in chat. The hook fails open: any crash is
   logged to stderr and the file write is never blocked.

### What flips a verdict

| Verifier | PASS | FAIL |
|---|---|---|
| `latex-verifier` | No `error`-severity findings | 1+ `error` findings |
| `citation-verifier` | No `mismatched` rows | 1+ `mismatched` rows |

`warning` (LaTeX) and `unresolved` / `skipped` (citations) never flip
the verdict, but `unresolved` rows trigger a transparency disclosure
on PASS.

### Scope: what the verifiers do NOT catch

The verifiers are **signature-based**, not semantic. They are a
backstop for one specific failure mode each, not a general
truthfulness check. Out of scope by design:

- **Book / textbook citations** — no public structured resolver.
- **Intra-document cross-references** (`see also the … section
  above`) — not citations.
- **Bare author-year mentions** without an arXiv ID, DOI, or URL
  (`Tishby & Pereira (2000)`).
- **Citations to slide decks, lecture notes, or private documents.**
- **Mathematical correctness** — `latex-verifier` only checks
  syntax / structure, never whether an equation is mathematically
  right.
- **Citation appropriateness** — `citation-verifier` only checks
  that the cited record exists and the claimed metadata matches.
  Whether the citation supports the surrounding claim is the Tutor's
  responsibility.

The Tutor remains solely responsible for honesty on these
(`ml-tutor/SKILL.md` R3: paper-bound vs general-knowledge framing).

### Per-paper citation cache

Resolver output is cached at `papers/<slug>/.cache/citations/`
keyed by `(kind, id)`. Survives across Tutor turns within a session.
Cache clearing at session end is on the roadmap (see `ROADMAP.md`).

### Tool layer

- `tools/verify_latex.py` — pure-Python LaTeX lexer (v1). Eight
  rules across six families, all scoped to math blocks except
  `forbidden-delim` and `dollar-balance` (whole document). KaTeX
  strict-mode renderer (v2) is planned for the Linux machine.
- `tools/verify_citations.py` — detector + resolver. Resolvers:
  arXiv Atom API → Crossref REST API → firecrawl CLI (fallback for
  arXiv/DOI 404s and bare URLs). Claimed metadata parsed from prose
  is matched against resolved metadata (60% title overlap, any
  claimed surname in resolved authors, year within ±1).

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
