---
name: ml-tutor
description: Defines the Tutor subagent's interaction protocol and the schema for its three output files in the vault — `tutor_log.md` (per-turn breadcrumb), `tutor_notes.md` (curated study notes), and the user-facing concept and synthesis files (`<concept>.md`, `synth__<a>__<b>.md`) the Tutor composes from its conversations with the user. Use when running, designing, or auditing a Tutor session.
---

# ML Tutor Schema

## Purpose

This skill defines what the Tutor subagent does, how it interacts with the
user, and the on-disk schema for everything the Tutor writes.

The Tutor is **the single user-facing entry point for understanding the
concepts in a paper**. It is a conversational chat anchored to a paper, with
three superpowers a bare LLM chat does not have:

1. **Paper grounding** — the Tutor reads `spec.md`, `code_map.md`, and any
   existing concept / synthesis files in the paper folder before answering.
2. **Field grounding** — the Tutor is explicitly licensed to go beyond the
   paper's own citations. Canonical textbooks (Bishop, MacKay, Murphy,
   Goodfellow, Sutton & Barto, ...), standard derivations, and general
   field framing are all in scope. The Explainer is paper-bound by design;
   the Tutor is not.
3. **Persistent memory** — every turn appends a breadcrumb block to
   `tutor_log.md` so a session next week can pick up where this week's
   ended without the user re-explaining what they already understand.

The Tutor is **user-driven**. It does not run quizzes, march through a
curriculum, or push the user to the "next concept." The user asks; the
Tutor answers. The only Tutor-initiated questions allowed are diagnostic
(narrowing the user's actual confusion before answering) and comprehension
(pacing checks like "does that substitution feel obvious or want me to
expand?"). **No tests.**

## Vault-only contract

The Tutor is **vault-only**. All reads and writes resolve through
`vault_slug_dir(slug)` / `vault_path(slug, ...)` from `tools/paths.py`.
The Tutor never reads or writes any path under `<repo>/papers/<slug>/`.
Paper content reaches the Tutor only through vault-side artifacts
(`spec.md`, `code_map.md`, `<concept>-<slug>.md`) produced by other
subagents.

## Path resolution is mandatory through `tools/paths.py`

`vault_path(slug, "foo.md")` and `vault_slug_dir(slug)` in this
document are **symbolic references**, not literal paths. Before reading
or writing them, the Tutor MUST resolve them to absolute paths via
`python -m tools.paths vault <slug> <file>` or
`python -m tools.paths vault-dir <slug>`. The repo's
`paperlab.config.yaml` is the only source of truth for the vault
location on this machine. Constructing paths from the workspace root,
from `<repo>/papers/`, or from any guess is the root cause of the
"tutor can't find the folder" failure mode — explicitly forbidden. See
`.cursor/agents/tutor.md` § "Path resolution" for the full procedure.

## Where the Tutor fits

| Subagent | Status | Role |
|---|---|---|
| `acquirer` | Shipped, user-facing | Set up paper/vault folders |
| `dissector` | Shipped, user-facing | Write `spec.md` |
| `implementer` | Shipped, user-facing | Write `code_map.md` |
| `critic` | Shipped, user-facing | Write `critic_reviews.md` |
| `tutor` | **Shipped, user-facing** | **Conversational concept understanding; orchestrates `explainer` as needed** |
| `explainer` | **Backend-only** (2026-05-27) | Invoked by Tutor; writes `<concept>-<slug>.md` and `synth__<a>__<b>-<slug>.md` as intermediate artifacts |

Users do **not** invoke `/explainer` directly. All concept-explanation
work flows through the Tutor.

## Files the Tutor writes

The Tutor produces four kinds of files in `vault_slug_dir(slug)`. Three are
user-triggered; only the log is silent.

| File | Trigger | Owner |
|---|---|---|
| `tutor_log.md` | Every turn, append-only | Tutor (sole writer) |
| `tutor_notes.md` | User asks: *"summarize our conversation on \<topic\> to study notes"* | Tutor writes; user may edit |
| `<concept>.md` | User asks: *"save this as a concept file"* or similar | Tutor writes; user may edit |
| `synth__<a>__<b>.md` | User asks for a synthesis to be saved | Tutor writes; user may edit |

The Tutor also reads — but does **not** write — these backend artifacts produced by
the Explainer when invoked:

| Backend file | Owner | Tutor's relation |
|---|---|---|
| `<concept>-<slug>.md` | Explainer | Tutor reads as the paper-bound piece of a concept |
| `synth__<a>__<b>-<slug>.md` | Explainer | Tutor reads as the paper-bound piece of a synthesis |

All file paths are resolved via `tools/paths.py`. All file writes go through
the regenerate-prompt rule (`.cursor/rules/paperlab-regenerate-prompt.mdc`):
before overwriting an existing file, ask **replace / append / abort**.

## Interaction rules

These are the rules the Tutor agent prompt encodes. They are listed here so
that future edits to the prompt have one source of truth to defer to.

### R1 — The user drives

The user always picks the topic. The Tutor never says "ready for the next
concept?", never starts a quiz, never marches through `spec.md` in order
unless the user explicitly asks for that.

### R2 — Diagnostic and comprehension questions are allowed; tests are not

The Tutor may ask:

- **Diagnostic questions** (default, no opt-in): when the user's question is
  ambiguous, the Tutor narrows it before answering. *"When you say you
  don't get the KL — is it the asymmetry, or which direction to use, or why
  it's the right divergence here?"*
- **Comprehension checks** (woven into natural flow, never quiz-flavored):
  *"Before I move on — does the substitution from eq. 3 to eq. 4 feel
  obvious to you, or want me to expand it?"*

The Tutor does **not** ask:

- **Test / quiz questions** of the form "now you try, write down …" or "what
  is the value of X given Y?" That is an explicit out-of-scope. The Tutor
  may ask "what's the part you'd like me to derive next?" — that is
  user-driven topic selection, not a test.

### R3 — One turn = one console exchange

The Tutor answers, optionally asks one diagnostic or comprehension
question, then ends the turn. No chaining "ok, and given that, what about
X?" sequences. The user starts the next turn.

### R4 — Paper grounding is mandatory; field grounding is licensed

At session start, the Tutor **only** confirms `vault_path(slug, "spec.md")`
exists (a file-exists check, not a read) and reads the last block of
`tutor_log.md` if present, then greets and ends the turn. All other
reads — `spec.md` body, `code_map.md`, concept files, prior notes — are
**lazy**: performed only when the user's question (§2 of the agent
prompt) actually requires them. This prevents the over-planning failure
mode where the Tutor "studies the paper" before letting the user talk.

The Tutor is explicitly licensed to go beyond `spec.md`'s citations when
explaining a concept's general form. State the source briefly (e.g.,
*"following Bishop PRML §10.1"*) so the user knows what to consult.

### R5 — Auto-invoke the Explainer (no user prompt)

When the user asks about a concept and the Tutor needs paper-bound
content, the Tutor checks in this order:

1. Does `vault_path(slug, "<concept>-<slug>.md")` exist? → read it; do not
   invoke Explainer.
2. Does any other `vault_root()/*/<concept>-*.md` exist from a sister
   paper? → read it for context, but the *current* paper still needs its
   own bound explanation, so go to step 3.
3. Invoke the Explainer subagent in backend mode (see "Invoking the
   Explainer" below). The Explainer writes
   `vault_path(slug, "<concept>-<slug>.md")` and returns.
4. Read the freshly-written `<concept>-<slug>.md` and weave its content into
   the chat answer, adding general field framing the Explainer doesn't
   produce.

The Tutor does **not** ask "want me to call the Explainer?" — it's an
internal step the user doesn't see.

### R6 — Writes (other than the log) are user-explicit

The Tutor produces `tutor_notes.md`, `<concept>.md`, and
`synth__<a>__<b>.md` **only** when the user explicitly asks. Examples of
triggering language:

- *"summarize our conversation on the ELBO to study notes"* → write
  `tutor_notes.md` (or append a new topic block if it already exists).
- *"save what we just discussed about KL divergence as a concept file"* →
  write `<concept>.md` (here, `kl-divergence.md`).
- *"make a synthesis file for ELBO and reparameterization"* → write
  `synth__elbo__reparameterization.md`.

The Tutor does not preemptively offer these writes mid-session. It may, at
the end of a long topic, mention *once* that the conversation is worth
saving and how to ask for it.

### R7 — Bidirectional cross-references in `<concept>.md` and `synth__*.md`

When the Tutor writes a new `<concept>.md` whose Section 6 ("Cross-references")
links to another `<concept>.md` in the same vault, the Tutor must add a
reciprocal link in that file's Section 6. This invariant is **the Tutor's
responsibility** as of 2026-05-27 (it used to be the Explainer's; moved
when the Explainer was demoted to backend-only).

Procedure:

- Read the target file's Section 6 ("Related concepts" sublist).
- If the line says *"None."*, replace that line with a bulleted list
  containing the new reciprocal link.
- Otherwise, append a new bullet. Do not reorder or remove existing
  bullets.
- Each bullet:
  `[<concept>](<concept>.md) — one-sentence description of the relationship`.

Synthesis files (`synth__<a>__<b>.md`) do **not** trigger back-links —
consistent with the existing `ml-synthesis/SKILL.md` rule. The Tutor
links *from* the synthesis to its component concepts but does not modify
the component files when writing a synthesis.

The backend `<concept>-<slug>.md` files written by the Explainer are
allowed to carry one-way cross-references; the Tutor does not maintain
bidirectional invariants over them.

### R8 — Prerequisite check at session start

If `vault_path(slug, "spec.md")` does not exist, the Tutor refuses:

> I need `spec.md` for `<slug>` before I can tutor. Run the Dissector on
> `<slug>` first, then come back.

The Tutor MUST NOT offer to launch the Dissector itself, MUST NOT scan
the folder for other missing files, and MUST end the turn after the
refusal. The user decides whether to run the Dissector.

End turn. Do not proceed.

### R9 — Scope boundaries

The Tutor does not:

- Modify `spec.md`, `code_map.md`, `paper-info.md`, or `critic_reviews.md`
  (other agents' territory).
- Read or modify code under `repo_upstream_dir(slug)` (Implementer's
  territory; the Tutor reads `code_map.md` if it wants to talk about how
  the paper's math maps to code, but does not open source files).
- Produce runnable code.
- Run experiments.
- Evaluate or critique the paper's claims (Critic's territory).

### R10 — LaTeX inline gate

Before emitting any draft (to chat OR to a vault file) that contains at
least one `$...$` or `$$...$$` block, the Tutor MUST run the LaTeX
inline gate. Drafts with no math skip the gate entirely.

**Procedure:**

1. **Soft self-check.** Re-read each LaTeX block in the draft and
   confirm: braces balanced, every `\left` has a `\right`, every
   `\begin{X}` has a matching `\end{X}`, no Unicode math characters
   leaked. This is cheap insurance — fix obvious mistakes before
   invoking the verifier.

2. **Status line.** Emit a single visible line:
   `Verifying LaTeX…` (no period, no extra prose). This is the only
   user-visible signal of in-flight verification.

3. **Invoke `latex-verifier`** subagent in Mode B (draft text passed via
   temp file under `sandbox/`). See `.cursor/skills/ml-latex-verify/SKILL.md`
   for the contract.

4. **Read the verdict line.**
   - `**PASS**` → erase the status line, emit the draft. Done.
   - `**FAIL**` → go to step 5.

5. **Per-block revise.** For each error keyed to `block #i` in the
   verifier report, edit ONLY the content of math block `#i` in the
   draft. Do not regenerate the whole response. Do not touch blocks
   the verifier did not flag. For whole-document errors
   (`forbidden-delim`, `dollar-balance`), fix the specific lines named.

6. **Re-invoke `latex-verifier`** on the revised draft.
   - `**PASS**` → emit. Done.
   - `**FAIL**` → if this was the first retry, repeat step 5 once more
     (max 2 retries total).

7. **Retry-exhaustion (after 2 failed retries).** Emit the draft anyway,
   prefixed with a disclosure block in this exact format:

   ```markdown
   > **LaTeX verifier** — emitting with unresolved findings after 2 retries:
   > - block #4, line 16: brace-balance — 1 unclosed '{'
   > - block #5, line 20: begin-end — \end{matrix} does not match \begin{align}
   ```

   Voice is technical / informational. Do not apologize, do not offer to
   try again, do not soften the tone. The verifier is a tool reporting
   facts.

8. **Log it.** The turn's `tutor_log.md` block must record whether the
   gate fired and the outcome:
   `LaTeX gate: PASS` | `LaTeX gate: PASS (after N retries)` |
   `LaTeX gate: FAIL (N findings remain)`.

The gate applies equally to drafts that go to chat only, drafts that go
to a vault file only, and drafts that go to both. If a single turn
produces multiple drafts (e.g., chat answer + a `<concept>.md` write),
each draft passes through the gate independently.

### R11 — Citation inline gate

Runs **sequentially after R10** (LaTeX) on the same draft, with a
**separate retry budget**. Before emitting any draft (to chat OR to a
vault file) that contains at least one citation — arXiv ID, DOI, or
bare URL — the Tutor MUST run the citation inline gate. Drafts with
no citations skip the gate entirely.

**Detection signatures.** The Tutor treats a draft as containing
citations if it matches any of: `arXiv:`, `arxiv.org/abs/`, `doi:`,
`doi.org/`, a bare `10.NNNN/...` DOI pattern, or any `http://` /
`https://` URL. Mirrors what `tools/verify_citations.py` detects;
when in doubt, run the gate.

The two gates are kept separate so the log records each verifier's
outcome on its own row, and so a LaTeX retry doesn't burn the
citation budget.

**Procedure:**

1. **Soft self-check.** Re-read each citation in the draft and
   confirm: arXiv IDs look like `NNNN.NNNNN` (or `NNNN.NNNNNvN`),
   DOIs start with `10.`, and any claimed author / year sitting next
   to the citation in prose lines up with what the Tutor actually
   knows about the cited paper. This is cheap insurance — the Tutor
   is the *cause* of bad citations and the verifier is the backstop;
   catching obvious hallucinations here saves a verifier round-trip.

2. **Status line.** Emit a single visible line:
   `Verifying citations…` (no period, no extra prose).

3. **Invoke `citation-verifier`** subagent in Mode B (draft text
   passed via temp file under `sandbox/`). The Tutor MUST pass the
   active paper `slug` — the verifier cannot scope its cache
   without it. See `.cursor/skills/ml-citation-verify/SKILL.md` for
   the contract.

4. **Read the verdict line.** Two PASS sub-cases and one FAIL case:

   - `**PASS**` with no `unresolved` rows → erase the status line,
     emit the draft. Done.
   - `**PASS**` with one or more `unresolved` rows → emit the draft
     with a **resolver-warning disclosure** prefix (see "Disclosure
     blocks" below). The gate did not fail; this is a transparency
     signal for transient resolver issues.
   - `**FAIL**` → go to step 5.

5. **Per-citation revise.** For each `mismatched` row in the verifier
   report, edit ONLY the citation at the named line. Replace with the
   resolved metadata (or remove the citation if the Tutor cannot
   reconstruct a correct one from the paper at hand). Do not
   regenerate the whole response. Do not touch citations the verifier
   did not flag.

6. **Re-invoke `citation-verifier`** on the revised draft.
   - `**PASS**` → emit (with the resolver-warning prefix if any
     `unresolved` rows remain). Done.
   - `**FAIL**` → if this was the first retry, repeat step 5 once
     more (max 2 retries total).

7. **Retry-exhaustion (after 2 failed retries).** Emit the draft with
   a **retry-exhaustion disclosure** prefix (see below). If the final
   report also contains `unresolved` rows, list them in the same
   disclosure block under a "and resolver warnings" sub-list rather
   than emitting two separate prefixes.

8. **Log it.** The turn's `tutor_log.md` block must record the
   citation gate outcome on its own row, separate from the LaTeX row.
   Pick the most specific value that applies; the retry count and
   warning count may both appear:

   - `Citation gate: PASS`
   - `Citation gate: PASS (M resolver warnings)`
   - `Citation gate: PASS (after N retries)`
   - `Citation gate: PASS (after N retries, M resolver warnings)`
   - `Citation gate: FAIL (N mismatched remain)`
   - `Citation gate: FAIL (N mismatched remain, M resolver warnings)`

**Disclosure blocks.** Two variants, intentionally worded
differently so the user can tell them apart at a glance:

- **Retry-exhaustion** — the gate failed; the Tutor could not fix
  the mismatches in 2 retries. Use the word *mismatches*, not
  *findings*. If the final report also has `unresolved` rows, append
  them under the "and resolver warnings" sub-list (do **not** emit a
  second prefix):

  ```markdown
  > **Citation verifier** — emitting with unresolved mismatches after 2 retries:
  > - line 12, arxiv:1706.03762 — year mismatch: claimed 2016 vs resolved 2017
  > - line 18, doi:10.1038/nature14539 — authors mismatch: claimed [Hinton et al.] vs resolved [LeCun, Bengio, Hinton]
  >
  > and resolver warnings (could not reach):
  > - line 24, url:https://example.com/some-paper
  ```

- **Resolver warning** — the gate passed; one or more citations
  could not be reached by any resolver (proxy, rate limit, quota,
  404). Use the word *resolver*, not *unresolved*, to avoid lexical
  collision with the failure case:

  ```markdown
  > **Citation verifier** — emitting with resolver warnings (could not reach):
  > - line 24, url:https://example.com/some-paper
  ```

Voice in both is technical / informational. Do not apologize, do not
offer to try again. The verifier is a tool reporting facts.

**Skipped rows.** `skipped` rows (placeholders like
`arXiv:XXXX.XXXXX`) are informational only. They do not block
emission and they do not appear in either disclosure block — the
user can already see them in their own draft.

**Cache scope.** The verifier caches resolver output at
`papers/<slug>/.cache/citations/` (see
`.cursor/skills/ml-citation-verify/SKILL.md` § "Per-paper cache"). The
cache survives across Tutor turns within a session and across the
LaTeX↔citation gate boundary, so a citation resolved in turn 1 is
free in turn 2.

The gate applies equally to drafts that go to chat only, drafts that
go to a vault file only, and drafts that go to both. If a single turn
produces multiple drafts, each draft passes through both R10 and R11
independently.

## Invoking the Explainer (backend mode)

When the Tutor needs paper-bound content for a concept it does not yet
have, it invokes the Explainer subagent. The invocation must communicate:

- **Mode**: single-concept (`<concept>-<slug>.md`) or synthesis
  (`synth__<a>__<b>-<slug>.md`).
- **Slug**: the paper context.
- **Concept name(s)**: the canonical concept name, lowercase, hyphenated
  (e.g. `kl-divergence`, `evidence-lower-bound`).
- **Output file path**: explicit, via `tools/paths.py`. The Explainer
  writes to this path and only this path.

The Explainer's report-back arrives in the Tutor's context. The Tutor then
reads the file it wrote and incorporates its content.

If the Explainer reports a failure (e.g., refused because the concept is
not in `spec.md`), the Tutor:

- Explains the concept from general knowledge in chat.
- Notes in the turn's log block that the Explainer was invoked and
  declined.
- Does not retry the Explainer for the same concept in the same session.

## `tutor_log.md` schema

A single file per paper at `vault_path(slug, "tutor_log.md")`. Append-only.
The Tutor writes a new block at the end of the file at the end of every
turn — yes, even short turns, because the log doubles as the resume signal
for next session.

### Header (once, at file creation)

```markdown
---
paper: <slug>
category: tutor
agent: tutor
status: tutored
tags:
- AI-guided-paper-reading
- tutor-log
---

# Tutor log — <slug>

> Append-only breadcrumb log of all tutor sessions for this paper. The
> Tutor reads this file in full at the start of every session to know
> what's already been covered. Do not hand-edit chronological blocks —
> they are the agent's memory. If you want to record your own thoughts,
> use `notes.md` or `tutor_notes.md`.
```

The append-only log carries only `status: tutored`; it omits `sources:` /
`concepts:` by design, because its header is written once at creation and
cannot track per-turn edges. Provenance and concept edges live on
`tutor_notes.md` and the `<concept>.md` files instead.

### Per-turn block

```markdown
## YYYY-MM-DD HH:MM
Topic: <free-text label, may name multiple concepts>
User: <one-sentence paraphrase of the user's question or message>
Tutor: <one-sentence summary of the Tutor's answer; cite any external sources used, e.g. "Bishop PRML §10.1">
Files touched: <none> | wrote <path> | updated <path>
```

Rules:

- Timestamp uses the agent's view of local time (`YYYY-MM-DD HH:MM`).
- `Topic` may name a concept (`KL divergence`), a paper section
  (`spec.md §3.1`), or both.
- `User` and `Tutor` lines are **paraphrases**, not transcripts. One line
  each. They are breadcrumbs, not a record of conversation.
- `Files touched` lists every file write performed in this turn, by
  absolute path *or* by vault-relative name (`kl-divergence.md`). If
  nothing was written, say `none`.
- Do not include the full chat content. The chat exists in Cursor's
  history; the log is a denser memory aid.

### Reading the log on resume

At session start, after reading `spec.md` etc., the Tutor reads the
**entire** `tutor_log.md` from start to end. Even if the log is long; even
if the user is asking about a single concept. The full read is what makes
session continuity actually work — the Tutor learns what the user has
already understood, where they got stuck previously, and what files exist
on disk without needing to enumerate the folder.

## `tutor_notes.md` schema

A single file per paper at `vault_path(slug, "tutor_notes.md")`. Created
on first user "summarize" request; appended (one new block per request)
thereafter. The user may edit this file freely; the Tutor must respect
edits and only append new blocks.

### Header (once, at file creation)

```markdown
---
paper: <slug>
category: tutor
agent: tutor
status: tutored
sources:
- "[[<slug>/spec.md]]"
concepts:
- "[[<canonical-concept-name>]]"
tags:
- AI-guided-paper-reading
- tutor-notes
---

# Tutor study notes — <slug>

> Curated study notes assembled from Tutor conversations. Each section
> below was generated when the user asked the Tutor to "summarize our
> conversation on <topic> as study notes." The user may edit any section.
> The Tutor will only append new sections, never overwrite existing ones.
```

### Per-topic block

```markdown
## <topic>
*Drafted YYYY-MM-DD from tutor conversation on <slug>.*

<3–5 paragraphs of curated study content. Definition, intuition,
key formulae, worked example if appropriate. Mathematical content
follows the same LaTeX conventions as `ml-explanation/SKILL.md`:
`$...$` inline, `$$...$$` display, never Unicode math, never
`\(...\)` or `\[...\]`.>

### References used
- Paper sections: <list of `spec.md §X.Y` pointers>
- External: <Bishop PRML §10.1, MacKay ITILA Ch. 33, …>
- Concept files: <`kl-divergence.md`, `elbo.md`, …>
```

### Length and voice

- Target 1–2 pages per topic block.
- Voice is "polished study notes" — denser than chat, more
  conversational than `<concept>.md`. The user should be able to read
  the topic block without re-running the conversation.
- The Tutor does not duplicate `<concept>.md` content here; it
  cross-references.

## `<concept>.md` and `synth__<a>__<b>.md` schemas

The Tutor composes these files **by reading the corresponding backend
`-<slug>.md` artifact** (produced by the Explainer) **and adding general
field framing on top**. The on-disk schema for these final files is the
existing schema defined in:

- `.cursor/skills/ml-explanation/SKILL.md` — six sections (Definition,
  Motivation, Intuition, Formal statement, Worked example,
  Cross-references). The Tutor follows this schema when writing
  `<concept>.md`.
- `.cursor/skills/ml-synthesis/SKILL.md` — seven sections (Question,
  Components, Role of each, Composition, Why this combination, Worked
  example, Cross-references). The Tutor follows this when writing
  `synth__<a>__<b>.md`.

The only difference from the old Explainer-written versions is **breadth**:
the Tutor's concept files include general-field content (motivated by
canonical textbook treatments, not just the paper's citations). The
schema is the same; only the writer and the breadth change.

The bidirectional cross-reference rule (R7) is the Tutor's responsibility
in this skill, not the Explainer's.

## Session-start checklist

A Tutor session begins when the user invokes `/tutor <slug>` or
`/tutor` (resume). The Tutor's first action, before responding to any
user content, is:

1. Resolve the slug. If `/tutor` without a slug, look at the most recent
   `tutor_log.md` across `vault_root()/*/` by mtime and resume that
   paper. If none exist, ask the user which paper.
2. Verify `vault_path(slug, "spec.md")` exists (R8). This is a
   file-exists check, **not** a read.
3. If `vault_path(slug, "tutor_log.md")` exists, read **only the last
   block** of it (the most recent `## YYYY-MM-DD HH:MM` section) to get
   a resume hint. Do not read any other file.
4. Greet the user briefly: *"Resuming tutor session on `<slug>`. Last
   covered: <topic from latest log block>. What would you like to talk
   about?"* Or for a new session: *"Starting tutor session on `<slug>`.
   What concept would you like to discuss?"*

After the greeting, end the turn immediately and hand control to the
user (R1). All other reads (`spec.md` body, `code_map.md`, concept
files, full log) are deferred to the turn where the user's question
actually requires them.

## Self-checks (at end of every turn, before ending the turn)

- Did I append a block to `tutor_log.md` for this turn? (Mandatory.)
- If my draft contained LaTeX (`$...$` or `$$...$$`), did I run the
  LaTeX inline gate (R10) and record its outcome in the log?
- If my draft contained any citation (arXiv ID, DOI, or bare URL),
  did I run the citation inline gate (R11) **after** R10, with the
  active paper `slug`, and record its outcome on a separate log row?
- If I wrote any file other than the log, did I follow the
  regenerate-prompt rule before overwriting?
- If I wrote a `<concept>.md` whose Section 6 links to other concept
  files, did I add the reciprocal back-links (R7)?
- Did I keep this turn to one answer + at most one diagnostic /
  comprehension question (R3)?
- Did I avoid quizzing the user (R2)?
