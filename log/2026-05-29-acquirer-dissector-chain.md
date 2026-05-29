# 2026-05-29 — Acquirer → Dissector workflow chain + Dissector LaTeX gate

Paste the block below into a fresh chat to resume cleanly without
re-deriving today's decisions.

## What shipped today

Two workflow changes to the acquire → dissect pipeline, plus a
fresh-clone setup pass. **Not yet committed** at time of writing — files
are edited on disk.

### 1. Acquirer `rerun <slug>` mode
- New invocation alongside `acquire <slug> <url>`. For papers already in
  the workspace: re-derives checklist state, downloads only what's
  missing, refreshes metadata (commit SHA, repo-URL re-scan), regenerates
  `paper-info.md` to the current schema.
- Requires the paper to already exist (repo or vault folder), else
  directs the user to `acquire`.
- Carries implicit replace authorization for `paper-info.md` (overwrite +
  warn, no prompt).

### 2. Acquirer → Dissector auto-chain
- One user action: after a successful acquire (**PDF present**), the
  Dissector runs automatically, no user input.
- PDF is the sole gate. Missing supplements / upstream repo are
  non-blocking.
- PDF missing → Acquirer surfaces an `AskQuestion` manual-download prompt
  and does NOT dissect. User places PDF, runs `rerun` to resume.

### 3. Enforcement: hook, not just prompt
- `tools/hooks/dissect_on_acquire.py` — fires on `afterFileEdit` when
  `paper-info.md` is written (Acquirer's guaranteed final write in both
  modes), gates on `repo_pdf_path(slug)` existence, injects
  `additional_context`:
  - PDF present → "invoke the Dissector for `<slug>`, overwrite + warn on
    existing `spec.md`".
  - PDF missing → "do NOT dissect; surface manual-download + `rerun`
    prompt".
- **Why `paper-info.md` is the trigger, not "PDF appeared":** a manual
  file drop fires no agent event, so triggering on PDF presence would
  never catch the manual-download flow. `paper-info.md` write + PDF gate
  covers both flows; `rerun` is the re-entry point after manual download.
- Registered as the 2nd `afterFileEdit` hook in `.cursor/hooks.json`
  (NOTE: `.cursor/hooks.json` is write-protected for the agent — user
  edited it manually). Fails open. Mirrors `verify_on_vault_write.py`.
- Smoke-tested: GIB (present → dissect), FakePaper (missing → prompt),
  `spec.md` write (no-op `{}`).

### 4. Dissector inline LaTeX gate
- Dissector is now LaTeX-gated (like Tutor / Explainer), not
  post-hoc-only. After writing `spec.md`: invoke `latex-verifier`
  (Mode A on file) → fix error-severity findings → re-verify → retry
  budget max 2 → disclose remaining errors if budget exhausted.
- Post-hoc hook still runs on `spec.md` writes and additionally checks
  citations.

### 5. Regenerate-prompt exception
- `.cursor/rules/paperlab-regenerate-prompt.mdc` gained a scoped
  exception: `rerun` + auto-dissect may overwrite `paper-info.md` /
  `spec.md` without the replace/append/abort prompt, but MUST warn.
  Scoped to those two files only.

## Validation
- Live `/acquirer rerun GIB` run by the user: worked as planned.
- CIGA `spec.md` had a real `brace-balance` error (line 33, unclosed
  `_{` subscript) — fixed manually, re-verified clean. Confirms the new
  gate catches a real (v1-lexer-class) failure mode.

## Files touched
- `.cursor/agents/acquirer.md` — acquire/rerun modes, PDF gate, auto-dissect handoff, reporting.
- `.cursor/agents/dissector.md` — invocation paths, inline LaTeX gate (step 8 + section), reporting.
- `.cursor/skills/ml-acquisition/SKILL.md` — two modes, auto-dissect policy, PDF-missing branch.
- `.cursor/skills/ml-paper-spec/SKILL.md` — LaTeX verification gate section.
- `.cursor/rules/paperlab-regenerate-prompt.mdc` — auto-chain exception.
- `tools/hooks/dissect_on_acquire.py` — NEW hook.
- `.cursor/hooks.json` — registered the new hook (user edited; agent write-blocked).
- `C:/.../PaperLab/CIGA/spec.md` — fixed brace-balance error.

## Fresh-clone setup (this machine)
- `paperlab.config.yaml` created from example: `repo_root` =
  `C:/Users/e0482362/Workspace/paperlab-cursor`, `vault_paperlab_path` =
  `C:/Users/e0482362/OneDrive - Sanofi/Workspace/Topics/public/Modeling/PaperLab`,
  `obsidian_vault_root` = `C:/Users/e0482362/OneDrive - Sanofi/Workspace`.
- `papers/` created. Only `papers/GIB/GIB.pdf` present locally; other 8
  vault papers (CIGA, DoFormer, Dreamer, GraphVarBound, IGL, MIbound,
  VAE, WorldModel) have vault notes but no local source PDF.
- Repo-local `.venv` (Python 3.12.1) created, `requirements.txt`
  installed, `.venv/` added to `.gitignore`. Path resolution + both
  verifier tools confirmed working in venv.

## Caveat carried forward
- LaTeX gate is v1 lexer (~70% coverage). Render-time errors (undefined
  macros, wrong arg counts) slip through until v2 KaTeX renderer
  (Linux-machine TODO). Brace / delimiter / `$`-balance solidly covered.

## Still deferred (unchanged from 2026-05-28)
1. Cache clearing at Tutor session end.
2. KaTeX strict-mode renderer for LaTeX v2 (Linux machine).
3. Planned units: `prerequisite`, `experimenter` subagents.

## Handoff block (paste this into a fresh chat)

```
Context handoff — 2026-05-29 — acquirer/dissector workflow chain

WHAT SHIPPED (edited on disk, NOT yet committed)
1. Acquirer `rerun <slug>` mode (alongside `acquire`): refreshes existing
   paper, regenerates paper-info.md to current schema, implicit replace
   authorization for paper-info.md (overwrite + warn).
2. Acquirer -> Dissector auto-chain: after successful acquire (PDF
   present), Dissector runs automatically, no user input. PDF is sole
   gate. PDF missing -> AskQuestion manual-download prompt, no dissect;
   user runs `rerun` to resume.
3. Hook tools/hooks/dissect_on_acquire.py fires on afterFileEdit when
   paper-info.md is written, gates on repo_pdf_path(slug) existence,
   injects additional_context (dissect vs. download-prompt). Registered
   as 2nd afterFileEdit hook in .cursor/hooks.json (user edited it; agent
   write-blocked). Fails open. Trigger on paper-info.md (not "PDF
   appeared") because manual file drops fire no agent event.
4. Dissector inline LaTeX gate: latex-verifier Mode A on spec.md ->
   fix -> retry x2 -> disclose. Post-hoc hook still does citations.
5. paperlab-regenerate-prompt.mdc: scoped exception — rerun + auto-dissect
   overwrite paper-info.md/spec.md without prompt but MUST warn.

VALIDATION
- /acquirer rerun GIB worked (user-run).
- Hook smoke-tested: GIB present->dissect, fake slug missing->prompt,
  spec.md write->no-op.
- CIGA spec.md brace-balance error (line 33, unclosed _{ ) fixed +
  re-verified clean. Real v1-catchable failure mode.

FILES TOUCHED
- .cursor/agents/{acquirer,dissector}.md
- .cursor/skills/ml-acquisition/SKILL.md, ml-paper-spec/SKILL.md
- .cursor/rules/paperlab-regenerate-prompt.mdc
- tools/hooks/dissect_on_acquire.py (NEW), .cursor/hooks.json
- vault CIGA/spec.md (bug fix)

FRESH-CLONE SETUP (this machine)
- paperlab.config.yaml created (repo_root, vault_paperlab_path,
  obsidian_vault_root filled). papers/ created. Only papers/GIB/GIB.pdf
  present locally. Repo-local .venv (3.12.1) + requirements.txt; .venv/
  gitignored.

CAVEAT
- LaTeX gate v1 lexer (~70%). Render-time errors slip through until v2
  KaTeX (Linux). Brace/delimiter/$-balance covered.

STILL DEFERRED
1. Tutor session-end cache clearing.
2. KaTeX v2 (Linux).
3. prerequisite, experimenter subagents.
```
