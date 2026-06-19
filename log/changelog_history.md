# PaperLab changelog history

Completed-work history, moved out of `ROADMAP.md` so the roadmap stays
forward-looking. Most recent at the top. For the per-session decision
narratives, see the dated logs in this folder.

## Recently completed (2026-06-04 → 2026-06-18, experimenter suite completion + schema refinements)

The Experimenter suite finished shipping and two `ml-evaluation` schema refinements landed. Per-agent roles live in the `ROADMAP.md` Agents table; dated logs carry the full narrative.

- **`coder` — both stages shipped.** Stage 1 (user-invokable, `/coder code <slug>`, 2026-06-04) writes `method.py` + `test_invariants.py` to `vault_code_dir(slug)`. Stage 2 (backend) has two regimes: component surgery (≥ 2 papers, 2026-06-04) and extension regime (1 paper, 2026-06-16). See `log/2026-06-03-two-stage-coder-design.md`, `log/2026-06-04-stage2-regime2-component-surgery-design.md`, `log/2026-06-16-critic-code-review-and-coder-extension.md`.
- **`coder` smoke gate (2026-06-18).** The previously-parked "does it run?" check wired into Stage 2 (`run.py --smoke`, per-machine timeout via `coder_runtime_timeouts()`, two-invocation flow with the critic gate between). See `log/2026-06-18-coder-smoke-gate-design.md`.
- **`critic` code-review split + extension-fidelity (2026-06-16).** `reconstructed`-source audit writes `code_review.md` (sibling of `critic_reviews.md`); new extension-fidelity gate mode. See `log/2026-06-16-critic-code-review-and-coder-extension.md`.
- **`evaluator` shipped 2026-06-17** (backend-only). Reads `design.md` + run-result JSON; writes `findings.md`. No PASS/FAIL; `[INSUFFICIENT-RUN]` on under-spec runs. See `log/2026-06-17-evaluator-build.md`.
- **`experimenter` — skill + command conversion (2026-06-15), Build-evaluate + filesystem-state topic detection (2026-06-17).** Loaded via `/experimenter <topic>`. See `log/2026-06-17-evaluator-build.md` and the Agents table.
- **`external-fetch-budget.mdc` rule (2026-06-18).** Per-session (≤ 20) and per-task (≤ 7) fetch caps for budget-bearing agents, asymmetric reset-on-confirm. See `log/2026-06-18-external-fetch-budget.md`.
- **Inline LaTeX gate (no citation gate) on `design.md` / `findings.md` (2026-06-18).** See `log/2026-06-18-experimenter-evaluator-latex-gate.md`.
- **`ml-evaluation` schema refinements (2026-06-18, moved from ROADMAP § Schema improvement candidates 2026-06-19):**
  - **Gating-hypothesis rule** — `[GATED-OFF]` flag + `### Gating hypotheses` subsection for hypotheses whose interpretability is conditional on another being supported. See `log/2026-06-17-evaluator-experimenter-gaps.md` § Gap 4, `log/2026-06-18-evaluator-schema-followups.md`.
  - **Table-cell tagging convention** — structural-cell exception to the `[A]`/`[B]`/`[E]` rule (don't tag controlled-vocabulary `Status` / flag `Notes` cells).

## Recently completed (2026-06-02, experimenter shell + reindex v1 + graph groundwork)

Three connected pieces landed this session.

- **Graph-index front-matter groundwork (Phase 1).** Added `status`,
  `sources`, `concepts` keys to the artifact front-matter schema
  (`AGENTS.md` "Graph index groundwork"), propagated to the six generator
  skills, and created `.cursor/skills/concept-vocabulary.md` (grow-on-
  demand canonical concept list). Keys are inert until a reader exists,
  but double as Obsidian backlinks today. `comparison.md` uses
  `status: compared` (multi-paper, outside the linear pipeline).
- **`tools.reindex` v1.** Deterministic read-only parser that walks the
  vault, parses front-matter + body `[[wiki-links]]`, and emits
  `graph.json` under `vault_index_dir()` (`<vault>/.index/`). Nodes:
  papers / topics / artifacts / concepts. Edges: `has_artifact`,
  `includes_paper`, `has_status`, `derived_from`, `mentions`. Drift
  report to stderr. CLI: `python -m tools.reindex [--check]`. Added
  `vault_index_dir()` to `tools/paths.py`. Three design questions
  resolved: link-only (no staleness hashing), report-only concept drift,
  JSON-only. First run: 45 nodes / 31 edges over the legacy vault (only
  `has_artifact` fired — test papers predate the schema, deliberately not
  backfilled). v2 directions (staleness, graph-consulting agents,
  lifecycle queries, rollup) captured in Planned units §5.
- **`experimenter` design-phase shell.** Second agent of the suite.
  `.cursor/agents/experimenter.md` + `.cursor/skills/ml-experiment-design/SKILL.md`.
  User-facing orchestrator scoped to the **design phase**: conversational
  design ⇄ user (criterion → methods → hypotheses → data → MVP →
  rationale), conceptual trade-offs via backend `comparator`, optional
  critic advisory (consult `critic_reviews.md` if present, never force —
  un-parks §12 of the design log), writes `design.md` (`status: designed`)
  with an inline LaTeX + citation gate. Stops at the implement boundary;
  `findings.md` schema documented but write-path deferred to the
  `evaluator`. Build order: `comparator` ✅ → `experimenter` shell ✅ →
  `coder` → `evaluator`.

## Recently completed (2026-05-29, comparator shipped)

First agent of the Experimenter suite. Build notes in
[`2026-05-29-experimenter-design.md`](./2026-05-29-experimenter-design.md) §11.

- **`comparator` agent + `ml-comparison` skill.** Dual-mode conceptual
  comparison of 2+ papers' methods along a user-chosen axis. Resolves
  slugs/axis/topic (asks if missing; needs ≥ 2 papers), may refine a
  vague axis via propose-and-confirm, reads `spec.md` (+ `code_map.md` /
  PDF when needed), writes `comparison.md` to
  `vault_experiments_dir(topic)`. 8-section schema with multi-paper
  front-matter (`topic:` + `papers:` list), notation reconciliation, and
  the critic's `[A]`/`[B]` inference discipline (forbidden `[C]`).
- **Inline verification gate (both LaTeX + citations).** The comparator
  is the first agent to gate *both* inline (Tutor/Explainer gate both on
  draft text; Dissector gates only LaTeX inline). Needed because the
  post-hoc hook can't handle the multi-paper layout.
- **Post-hoc hook skips `experiments/`.** `verify_on_vault_write.py`
  returns a no-op skip for the `experiments/<topic>/` tree (no single
  `<slug>` for its log/cache model). Smoke-tested.
- **PDF text promoted to a visible copy.** `tools/pdf.py` now caches
  extracted text as `papers/<slug>/<slug>.txt` (supplements:
  `<slug>-<source>.txt`) instead of the hidden `.cache/`. Any agent can
  read the paper text directly. CIGA's cache migrated.
- **Verified:** both verifier tools run clean on a comparison-style file
  (LaTeX PASS; arXiv citation resolved 1/1); hook skip confirmed; no
  lint regressions.
- **Parked (for the `experimenter`):** optional critic advisory during
  the design phase (consult `critic_reviews.md` if present, never force).

## Recently completed (2026-05-29, later)

Experimenter suite **design session** (no agent/skill files yet — design
+ scaffolding only). Full decision log in
[`2026-05-29-experimenter-design.md`](./2026-05-29-experimenter-design.md).

- **Re-scoped the `experimenter`** from a single-paper toy scaffolder
  into a **multi-paper, problem-type-oriented, full-lifecycle**
  comparison suite of four agents: `experimenter` (user-facing
  orchestrator), `comparator` (dual-mode conceptual comparison, un-parked),
  `coder` (backend scaffold+run), `evaluator` (backend empirical
  interpretation).
- **Locked the interaction model — Model 3 (hybrid):** `coder` does the
  heavy scaffold one-shot; `experimenter` does the tight write→check→tweak
  loop in-session. Mirrors the proven tutor/explainer split. The
  one-shot-vs-in-session trade-off is the documented rationale.
- **Split conceptual from empirical comparison:** `comparator` (prose,
  from specs, dual-mode) vs. `evaluator` (numbers, from run outputs,
  backend-only, routes through `experimenter`).
- **Locked file layout:** notes/design in vault
  `<vault>/experiments/<topic>/`; code/data in repo
  `sandbox/experiments/<topic>/` (`synth/`, `methods/`, `run/`,
  `results/`, git-ignored `data/`). `<topic>` user-chosen; `experiments/`
  namespace avoids collision with `sandbox/<slug>/`.
- **Shipped path helpers:** `repo_experiments_dir(topic)` and
  `vault_experiments_dir(topic)` in `tools/paths.py`, with CLI verbs
  `exp-sandbox` / `exp-vault`. Both resolve from existing config keys —
  no new config key needed. Verified resolving on this machine.
- **Shipped `.gitignore` carve-out:** `sandbox/experiments/` re-included
  from the blanket `sandbox/` ignore; only `sandbox/experiments/*/data/`
  stays ignored. Verified: code tracked, data ignored, other `sandbox/`
  still ignored.
- **`implementer` left as-is**, coder verifier gate parked. Build order:
  `comparator` first, then `experimenter` → `coder` → `evaluator`.

## Recently completed (2026-05-29)

Acquirer → Dissector workflow tightening, plus a fresh-clone setup pass.

- **Acquirer `rerun <slug>` mode.** New invocation alongside `acquire`,
  for papers already in the workspace. Re-derives checklist state,
  downloads only what is missing, refreshes derived metadata (commit
  SHA, repo-URL re-scan), and regenerates `paper-info.md` against the
  current schema. Requires the paper to already exist (repo or vault
  folder). Carries implicit replace authorization for `paper-info.md`
  (overwrite + warn, no prompt). Documented in `.cursor/agents/acquirer.md`
  and `ml-acquisition/SKILL.md`.
- **Acquirer → Dissector auto-chain (single user action).** After a
  successful acquire (PDF present), the Dissector runs automatically
  with no user input. The PDF is the sole gate — missing supplements /
  upstream repo are non-blocking. If the PDF is missing, the Acquirer
  surfaces an `AskQuestion` manual-download prompt and does **not**
  dissect; the user places the PDF and runs `rerun` to resume.
- **Enforcement via hook, not just prompt.** `tools/hooks/dissect_on_acquire.py`
  fires on `afterFileEdit` when `paper-info.md` is written (the
  Acquirer's guaranteed final write, in both `acquire` and `rerun`),
  gates on `repo_pdf_path(slug)` existence, and injects
  `additional_context` telling the agent to either dissect (PDF present)
  or surface the download prompt (PDF missing). Triggering on
  `paper-info.md` + gating on the PDF covers both flows, including the
  manual-download case where dropping a file fires no agent event.
  Registered as the second `afterFileEdit` hook in `.cursor/hooks.json`.
  Fails open, mirrors `verify_on_vault_write.py` conventions. Smoke-tested
  on GIB (present → dissect), a fake slug (missing → prompt), and a
  non-`paper-info.md` write (no-op).
- **Dissector inline LaTeX gate.** The Dissector is now a LaTeX-gated
  agent (like Tutor / Explainer), not post-hoc-only. After writing
  `spec.md` it invokes the `latex-verifier` (Mode A on the file), fixes
  error-severity findings, re-verifies, retry budget max 2, and discloses
  remaining errors if the budget is exhausted. Documented in
  `.cursor/agents/dissector.md` and `ml-paper-spec/SKILL.md`. The post-hoc
  hook still runs on `spec.md` writes and additionally checks citations.
- **Regenerate-prompt exception.** `.cursor/rules/paperlab-regenerate-prompt.mdc`
  gained a scoped exception: the `rerun` + auto-dissect chain may
  overwrite `paper-info.md` and `spec.md` without the replace/append/abort
  prompt, but **must warn** in the report. Scoped to those two files only.
- **Caught a real error with the new gate's tool.** CIGA `spec.md` had a
  `brace-balance` error (line 33, unclosed `_{` subscript group) — a
  v1-lexer-catchable class the inline gate would have blocked at emit
  time. Fixed manually; re-verified clean. Confirms the gate addresses a
  real failure mode, not a hypothetical one.
- **Fresh-clone setup.** This machine was a fresh clone: created
  `paperlab.config.yaml` from the example (filled `repo_root`,
  `vault_paperlab_path`, `obsidian_vault_root`), created `papers/`, and
  built a repo-local `.venv` (Python 3.12.1) with `requirements.txt`
  installed; added `.venv/` to `.gitignore`. Path resolution and both
  verifier tools confirmed working in the venv.

**Caveat carried forward.** The LaTeX gate uses the v1 lexer (~70%
coverage). Render-time errors (undefined macros, wrong arg counts) still
slip through until the v2 KaTeX renderer lands (Linux-machine TODO).
Brace / delimiter / `$`-balance errors are solidly covered.

## Recently completed (2026-05-28)

End-to-end verifier system shipped. Two read-only backend subagents
(`latex-verifier` and `citation-verifier`), two pure-Python tools,
two trigger paths (inline gate + post-hoc hook), and documentation
across the Tutor and Explainer agent/skill files.

- **`tools/verify_citations.py` — citation detector + multi-tier
  resolver.** Detects arXiv IDs (`arXiv:NNNN.NNNNN`,
  `arxiv.org/abs/...`), DOIs (`10.NNNN/...`, `doi:...`,
  `doi.org/...`), and bare URLs. Three-tier resolution: arXiv Atom
  API → Crossref REST API → firecrawl CLI fallback. Claimed
  metadata parsed from prose (markdown-link text when title-shaped,
  `Author et al., YYYY` patterns on the citation's line + previous
  line). Judgment against resolved fields: 60% title token-overlap,
  any claimed surname in resolved authors, year within ±1. Per-paper
  cache at `papers/<slug>/.cache/citations/<sha1(kind:id)>.json`
  keyed by `(kind, id)`. Exit code 1 only on `mismatched`;
  `unresolved` is a warning (transient resolver issues are common
  for valid citations). Smoke-tested on a synthetic fixture with
  the Transformer paper, LeCun et al. 2015, and an unresolvable URL.
- **`firecrawl_cli()` helper in `tools/paths.py`.** Resolves the
  firecrawl CLI absolute path through `shutil.which` first, then
  the Windows scoop persist directory fallback
  (`%USERPROFILE%/scoop/persist/nodejs/bin/firecrawl.cmd`). Raises
  `FileNotFoundError` with install instructions when neither path
  works. Added to the `python -m tools.paths firecrawl` CLI
  dispatcher. Solves the corporate-Windows-PATH-not-propagating-to-
  spawned-shells issue documented during the firecrawl setup
  journey.
- **`.cursor/skills/ml-citation-verify/SKILL.md`** — mirrors the
  `ml-latex-verify` shape exactly (Purpose, Resolver tiers,
  Per-paper cache, Two invocation modes, What detects, What judges,
  Status semantics, Output schema, Subagent contract, Scope
  boundaries, Self-checks). Documents that `mismatched` is the only
  gate-failing status; `unresolved` is a warning surfaced via
  disclosure block.
- **`.cursor/agents/citation-verifier.md`** — read-only backend
  subagent. `readonly: true` with one documented escape hatch
  (Mode B temp file in `sandbox/`, mirroring `latex-verifier`).
  Explicitly isolated from forwarded context — judges only from the
  tool's JSON output to avoid trust-pressure from the calling agent.
- **`ml-tutor/SKILL.md` § R11 — Citation inline gate.** Runs
  sequentially after R10 (LaTeX) on the same draft with a separate
  retry budget (max 2 each). Detection signatures spelled out
  explicitly (`arXiv:`, `arxiv.org/abs/`, `doi:`, `doi.org/`, bare
  `10.NNNN/...`, any `http(s)://`). Soft self-check before invoking
  the verifier ("the Tutor is the cause, the verifier is the
  backstop"). Two disclosure templates intentionally worded
  differently — retry-exhaustion uses "mismatches", resolver
  warnings use "could not reach" — so the user can tell them apart
  at a glance. Six log-row values cover every combination of
  (no-retries / N-retries / FAIL) × (no-warnings / M-warnings).
- **`.cursor/agents/tutor.md` § "Citation inline gate (R11)" and
  `.cursor/agents/explainer.md` § 3.6** mirror the skill, with the
  Explainer using HTML-comment disclosures (file-write context, no
  user-facing chat).
- **`tools/hooks/verify_on_vault_write.py` — post-hoc hook
  extended.** Runs both verifiers sequentially on any non-gated
  vault `.md` write. Each verifier fails independently — a LaTeX
  crash doesn't kill citations and vice versa. Writes two append
  blocks to `verifier_log.md` (one per verifier) and returns one
  combined `additional_context` message to the calling agent.
- **`AGENTS.md` "Verifier system" section** added: documents the
  two trigger paths (inline gate + post-hoc hook), what flips a
  verdict per verifier, per-paper cache scope, and the tool layer.
  `latex-verifier` and `citation-verifier` also added to "Cursor
  Subagents" and "Agent-To-Skill Mapping".

**Same-day follow-ups:**
- **Live smoke run on `/tutor GIB` with both gates active passed.**
  Tutor produced math and a book citation; LaTeX gate fired
  (`Verifying LaTeX…`) and resolved cleanly, citation gate
  correctly skipped (no arXiv/DOI/URL signatures — book citations
  are out of scope by design, see "Scope lesson" below).
- **Temp-file naming drift caught + fixed.** The Tutor improvised
  `sandbox/.tmp_latex_verify_notes.md` instead of the spec's
  `_<unix_timestamp>.md` suffix. Benign in isolation but a latent
  collision risk across concurrent gates. Hardened both verifier
  subagent files (`latex-verifier.md`, `citation-verifier.md`)
  with a normative "MUST use unix timestamp" clause, explicit
  rationale, and the exact anti-pattern called out by name.
  Commit `0a420e7`.

**Scope lesson worth recording.** The citation verifier is
signature-based, not semantic. Book citations, intra-document
cross-references (`see also the … section above`), bare author-year
mentions without an arXiv/DOI/URL, and citations to slide decks or
private documents are all **out of scope by design** — there is no
public structured resolver for them. The Tutor remains solely
responsible for honesty on these (`ml-tutor/SKILL.md` R3: paper-bound
vs general-knowledge framing). The verifier is a backstop, not a
replacement for the Tutor's judgment.

**Still deferred:**
- Cache clearing at Tutor session end (currently the cache
  survives across sessions; only an explicit
  `rm -rf papers/<slug>/.cache/` clears it).
- KaTeX strict-mode renderer for LaTeX v2 (Linux machine).

## Recently completed (2026-05-27 late)

Follow-up hardening after the morning ship, driven by first-use friction on `/tutor GIB`:

- **Tutor path-resolution made operationally explicit.** `.cursor/agents/tutor.md` now opens `# Process` with a "Path resolution" section spelling out the shell procedure: `vault_path(slug, "foo.md")` and `vault_slug_dir(slug)` are *symbolic* references that MUST be resolved via `python -m tools.paths vault[-dir] <slug> [file]`. Forbidden shortcuts (workspace-root guesses, `<repo>/papers/`, `./vault/`, hard-coded prior-session paths) are listed by name. §0 step 3 (the `spec.md` existence check) was rewritten to follow the procedure and to interpolate the resolved absolute path into the refusal message so resolution failure is visible at a glance.
- **Tutor session-start was over-eager.** §0 originally read every `*.md` in the vault folder before greeting, causing multi-minute "Planning next moves" hangs. Replaced with lazy ingestion: file-exists check on `spec.md` and last-block read of `tutor_log.md` only, then greet and end the turn. All other reads (`spec.md` body, `code_map.md`, concept files, full log) deferred to the turn where the user's question actually needs them. `ml-tutor/SKILL.md` R4 and the session-start checklist mirror the new flow.
- **Tutor was offering to launch the Dissector itself.** Out of scope. Added an explicit "Vault-only contract" subsection and a no-launching rule to `# Scope boundaries` in both `.cursor/agents/tutor.md` and `ml-tutor/SKILL.md`: if a prerequisite is missing, the Tutor names it and the responsible subagent, then ends the turn. Only the Explainer (backend mode) may be invoked.
- **Windows non-BMP vault-path bug diagnosed and worked around.** Repeated `/tutor GIB` failures resolved to two compounding issues: (a) `paperlab.config.yaml` pointed at `Modeling 🎓/PaperLab`, which on the user's machine had already been migrated to the ASCII `Modeling/PaperLab`; and (b) downstream `test -f` / `ls` invocations against paths containing non-BMP characters (`🎓`) fail on Windows even when `python -m tools.paths` resolves them correctly with UTF-8 stdout. Fix: pointed config at the ASCII path; documented the Windows constraint in `AGENTS.md` ("Windows path warning for `vault_paperlab_path`"), `paperlab.config.example.yaml` (comment block above the key), `ROADMAP.md` Known limitations, and a clarifying comment in `tools/paths.py`. Migration confirmed working: `python -m tools.paths vault GIB spec.md` resolves to the ASCII path and `test -f` succeeds.
- **First live smoke run on `/tutor GIB` passed** after the above fixes. Session opened cleanly, resolved both vault paths, ended turn on greeting.

## Recently completed (2026-05-27)

- **`tutor` subagent shipped + `explainer` demoted to backend.** The user-facing concept-understanding interface is now the `tutor` subagent (`/tutor <slug>`). The `explainer` is no longer user-invocable; it is a backend service the tutor calls when it needs paper-bound content. New files:
  - `.cursor/agents/tutor.md` — conversational, anchored to one paper, paper-grounded + field-grounded, persistent memory.
  - `.cursor/skills/ml-tutor/SKILL.md` — defines interaction rules (R1–R9), `tutor_log.md` breadcrumb schema, `tutor_notes.md` study-notes schema, and the bidirectional cross-reference invariant for `<concept>.md` (moved here from `ml-explanation/SKILL.md`).
  - Vault per-paper layout grows four entries: `tutor_log.md` (append-only, every turn), `tutor_notes.md` (user-triggered curated study notes), `<concept>-<slug>.md` and `synth__<a>__<b>-<slug>.md` (backend intermediates written by the demoted explainer).
- **Interaction model:** user drives; tutor never quizzes; diagnostic + comprehension questions allowed; one-turn-per-exchange discipline; auto-invokes explainer when `<concept>-<slug>.md` is missing; writes only the log silently — everything else is explicit user request.
- **Schema changes:** `ml-explanation/SKILL.md` and `ml-synthesis/SKILL.md` updated to document the two writers + two filenames (Tutor → `<concept>.md`, Explainer → `<concept>-<slug>.md`; similarly for synthesis). The bidirectional-link rule moved from Explainer to Tutor. `AGENTS.md` updated to reflect tutor as the user-facing concept entry point and explainer as backend.
- **What we deliberately deferred:** live smoke run on a real paper (will iterate based on first-use friction), pruning logic for long `tutor_log.md`, `prerequisite` / `experimenter` / `comparator` agents.

## Recently completed (2026-05-27 earlier)

- **Visualizer + figure-verifier removed from `main`, archived to branch + tag.** See `visualizer-todo.md` for the chronicle.

## Recently completed (2026-05-22)

- **Dictionary PDF reference card + sync hook** — replaces the previous `symbols/atlas.png` quick-glance grid with a real reference document.
  - `tools/build_dictionary_pdf.py` parses the three category tables in `DICTIONARY.md`, augments each row with a fifth **Symbol** column embedding the matching tile from `symbols/<id>.png`, and emits `.cursor/skills/ml-visualization/DICTIONARY.pdf` via ReportLab (no LaTeX / pandoc / Chromium needed). Landscape A4, repeating table headers, alternating row backgrounds. Run as `python -m tools.build_dictionary_pdf` (full rebuild) or `... --skip-tiles` (PDF only, ~3 s).
  - Sync semantics are list-level: every row in `DICTIONARY.md` appears in the PDF, but entries without a registered renderer in `build_symbol_sheet.RENDERERS` get a visible `— no tile —` placeholder, so drift between dictionary and tiles is reported inside the PDF itself. Current state: 72 rows total, 36 with tiles, 36 placeholders.
  - Small LaTeX→Unicode expander in the PDF builder so `$\sim$`, `$\theta$`, `$\rho$`, `$\mathbb{E}$`, etc. render legibly instead of leaking command names.
  - `tools/hooks/pre-commit` + `tools/hooks/README.md` — source-controlled git hook installed once per clone with `git config core.hooksPath tools/hooks`. When `DICTIONARY.md` is staged, the hook rebuilds the PDF and tiles, re-stages them, and aborts the commit on build failure. `git commit --no-verify` skips it for WIP.
  - `tools/build_symbol_sheet.py` lost its `_build_atlas()` step and `atlas.png` / `atlas.dot` are deleted. The PDF is now the canonical visual reference card.
- **Visualizer v2 schema + backend decision** — the v2 concept-picture generator's schema is locked in. Three resolved questions:
  - **Source of visual vocabulary:** `.cursor/skills/ml-visualization/DICTIONARY.md` (v0.1). 23 entities, 12 relations, 37 actions, each row carries canonical name + aliases + symbolic representation. Verb-only canonical action names; math-symbol convention for `≤ ≥ = ≈ Σ ∫`; three-step gap rule (compose → closest-with-label → text-arrow fallback `— [verb objective] →` → stop and report) so the visualizer never invents new symbols silently; atomicity rule (one action = one arrow).
  - **Rendering backend:** **graphviz**. Picked after a head-to-head on the same panel via matplotlib (manual layout, ~5 visible collisions), tldraw (auto-routing OK but no headless export from the current MCP), and graphviz (auto-layout + direct PNG/SVG, no Chrome/Node dependency). Graphviz wins for the scripted, automated path. Portable Windows binary installed at `tools/graphviz/Graphviz-14.1.5-win64/` (git-ignored except for README), Linux install via `apt install graphviz`. Resolver in `tools.paths.graphviz_dot()` returns the per-machine binary path.
  - **Validation:** dictionary stress-tested on three concepts as text-spec inventories (GraphVarBound §6.1 TRW-IS, GIB §3.1 Markov representation, Dreamer §6.2 latent imagination AC). All three rendered with ≤ 1 text-arrow fallback and ≤ 1 composition each; zero invented idioms. GIB Panel B (per-layer relay cell) rendered end-to-end on all three backends; graphviz output (`sandbox/GIB/dry-run-dict-panel-b-graphviz.png`) is the reference.
- **Symbol-sheet atlas** — `.cursor/skills/ml-visualization/symbols/` now contains one PNG + SVG tile per dictionary entry (35 of 72 entries covered for v0.1 — the high-traffic ones from the three validation runs) plus a composite `atlas.png`. Generated by `python -m tools.build_symbol_sheet`, which parses `DICTIONARY.md` for the entry IDs, hand-renders each tile via graphviz, and warns about (a) dictionary entries with no renderer and (b) registered renderers with no dictionary entry — so the two stay in list-level sync.
- **`tools.paths.graphviz_dot()`** — resolver added. Tries `tools/graphviz/Graphviz-*/bin/dot[.exe]` first (portable, per-machine, git-ignored), then falls back to system `dot` on PATH. CLI surface: `python -m tools.paths dot`. Lets the same scripts work on the Windows-no-admin laptop and the Linux-admin desktop without code changes.
- **SKILL.md wired to DICTIONARY.md** — `ml-visualization/SKILL.md` now defines the concept-picture workflow (text → thesis → dictionary inventory → gap rule → atomicity rule → picture spec → graphviz render → verify against thesis) and routes the concept-picture mode to graphviz in the format-selection table. The dictionary, the atlas, and the atomicity rule all have prose pointers from the skill.

### Validation runs (2026-05-22)

- **Three concept inventories** completed as text specs against the dictionary (GraphVarBound §6.1, GIB §3.1, Dreamer §6.2). Same shape across three paper styles: 19-24 direct dictionary hits, ≤ 1 composition, ≤ 1 text-arrow fallback, 0 invented idioms. Detailed inventories captured in chat transcript.
- **One concept rendered through three backends.** GIB Panel B (per-layer relay cell) under matplotlib (`sandbox/GIB/dry-run-dict-panel-b-relay-cell.png`), tldraw (canvas `byw8g492` on the tldraw cloud), and graphviz (`sandbox/GIB/dry-run-dict-panel-b-graphviz.png`). Zero dictionary entries failed to draw on any backend; all readability differences were backend-level (layout, fonts, dashed envelopes).

## Recently completed (2026-05-20)

- **LaTeX-in-charts policy resolved** — layered approach codified in `ml-visualization/SKILL.md`:
  - **Mermaid (default for structural diagrams):** atomic symbols use Unicode (`θ`, `μ`, `Σ`, `ℝ`, `zₜ`, `∇L`); compound expressions go in the right column and labels reference them as `(eq. N)`. Carved out as an exception in `AGENTS.md` to the "no Unicode math" rule — Mermaid labels only.
  - **TikZ via `marp-tikz-plus` (escalation for math-heavy diagrams):** verified end-to-end in Obsidian preview against the [kevinyuan/marp-tikz-plus engine](https://github.com/kevinyuan/marp-tikz-plus). Plate notation, commutative diagrams, expectations with subscripted distributions, `\mathbb` / `\mathcal` / fractions all render natively in node labels. Authoring rules captured: no `\documentclass`, no `\usepackage{tikz}`, allowed `\usepackage` set limited to the engine's supported list (`amsmath`, `amssymb`, `amsfonts`, `array`, `tikz-cd`, `pgfplots`, `circuitikz`, `chemfig`, `tikz-3dplot`), `\usetikzlibrary{...}` must precede `\begin{document}`, `[scale=2]` for Marp slides.
  - **Extract-first waterfall extended** to four priorities: extracted paper figure → TikZ (math-heavy) → Mermaid (structural flow) → drop.
  - **Pre-write check added for TikZ blocks** alongside the existing Mermaid check; the visualizer agent now reports both counts on completion.
  - **KaTeX/MathJax preprocessing rejected** as overkill given that TikZ handles the math-heavy case natively.
- **Visualizer pivot decided** — v1 (slide decks + viz markdown) will be replaced by v2, a concept-picture generator writing PNGs to `<vault>/<slug>/figures/`. Reference framework captured in `visualizer-todo.md`. Backend selection deferred pending tomorrow's continuation and Linux-machine feasibility.
- **Agents table added** to the top of the roadmap as a single source of truth for agent status, role, and invocation cues. To be kept up to date as agents ship / change role / park.

## Recently completed (2026-05-19)

- **`visualizer` subagent + `ml-visualization` skill** — produces Marp slide decks (`slides.md`) and per-concept visualizations (`<concept>__viz.md`) from `spec.md` / `code_map.md` / `<concept>.md`.
- **Extract-first waterfall** — visualizer prefers extracted paper figures over generated diagrams; Mermaid/TikZ/matplotlib/tldraw are documented fallbacks.
- **PDF figure extraction (`tools/figures.py`)** —
  - `list_figures` — caption parser; supports `Figure N` / `Table N`, single- and double-column PDFs.
  - `extract_figure` — caption-block-width crop heuristic: text-block complement on both axes, paragraph-shape filter to exclude table rows / figure-internal labels, table-caption-above-or-below fallback, manual-crop escape hatch via `papers/<slug>/.cache/figures/manual_crops.json`.
  - `extract_figure_to_vault` — copies the cached PNG into `<vault>/<slug>/figures/` and returns a **vault-relative** path so embeds work across drives / OneDrive.
  - `captions_by_component` — looks up figures by prose context.
  - CLI: `list`, `extract`, `extract-to-vault`, `by-component`.
- **Semantic figure tagging in `spec.md` §4.5** — dissector classifies each figure as `headline` / `result` / `qualitative` / `thumbnail` via a two-pass keyword + prose cross-check.
- **YAML front-matter `paper: <slug>`** — added to all agent-generated notes and slides for vault-side queries.
- **Slide layout routing by figure aspect ratio + source** — three Marp classes:
  - `split` — square/portrait figure (W/H < 1.4) or Mermaid/TikZ diagrams; two-column figure-left / prose-right.
  - `figure-top` — landscape figure (1.4 ≤ W/H < 2.5); figure spans full width above a short prose strip.
  - `figure-full` — panorama / large tables (W/H ≥ 2.5); figure fills the slide, italic caption only.
  - Mermaid/TikZ stay forced to `split` so they don't blow up the slide; only extracted figures get the wider classes. CSS lives in the external `paperlab.css` Marp theme.
- **Visualizer overwrite contract (no AskQuestion privilege)** — when `slides.md` / `<concept>__viz.md` already exists, visualizer emits a text prompt with path / size / mtime and asks **replace / append / abort?**, then ends the turn until the user replies.

### Validation runs

- **`WorldModel`**, **`VAE`** — visualizer end-to-end: content generation OK, vault-relative figure embeds OK, overwrite prompt OK.
- **`Memento`**, **`GIB-DS`** — figure extraction spot-checked; most figures and tables crop cleanly. A few imperfect crops remain (see `visualizer-todo.md` current limitations).

## Recently completed (2026-05-18)

- **File layout contract** — repo holds source material (`papers/<slug>/<slug>.pdf`, `supplementals/`, `upstream/<slug>/`); vault holds all agent-generated markdown flat under `<vault>/<slug>/`.
- **Per-machine config** — `paperlab.config.yaml` (git-ignored) + `paperlab.config.example.yaml` (committed). Keys: `repo_root`, `vault_paperlab_path`, `obsidian_vault_root`.
- **Path-resolution helper** — `tools/paths.py` exposes `vault_path`, `vault_slug_dir`, `repo_pdf_path`, `repo_paper_dir`, `repo_supplementals_dir`, `repo_upstream_dir`, `repo_sandbox_dir`, plus a `python -m tools.paths` CLI. UTF-8 stdout enforced for resolution, but `vault_paperlab_path` must be ASCII on Windows — see Known limitations.
- **Always-on rules:**
  - `paperlab-config-bootstrap.mdc` — every agent resolves paths through `tools/paths.py`; documents read/write conventions; defines slug rule (verbatim user input).
  - `paperlab-regenerate-prompt.mdc` — never silently overwrite existing files in the vault; ask **replace / append / abort**.
- **Sweep of all 5 agents + 6 skills** — every `papers/<slug>/...` write target replaced with `vault_path(...)`; source-material reads now go through `repo_*` helpers.
- **Acquirer** — now creates both repo folder and vault folder; writes `paper-info.md` to the vault with absolute links to repo-side material.
- **Dependencies** — `requirements.txt` with `PyYAML>=6.0`.
- **Bug fix** — slug-mangling: agents were lowercasing/hyphenating user-provided slugs. Bootstrap rule and acquirer agent now both enforce verbatim slug.

### Validation runs

- **`WorldModel`** (acquired from scratch end-to-end): acquirer, dissector, implementer all produced files in the correct repo/vault locations. Critic and tutor not yet exercised on this paper.
- **`Memento`** (pre-migration, in repo): left untouched per agreed plan; remains at `papers/Memento/`.
