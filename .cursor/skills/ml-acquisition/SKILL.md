---
name: ml-acquisition
description: Sets up the per-paper repo folder (`papers/<slug>/`) for source materials AND the per-paper vault folder (`<vault>/<slug>/`) for agent-generated notes. Acquires paper PDF, optional supplements, optional upstream repository clone, commit SHA, and writes `paper-info.md` to the vault. Use when acquiring, adding, initializing, downloading, or setting up an ML paper.
---

# ML Acquisition Schema

## Purpose

This file defines the PaperLab acquisition protocol: a scaffolded **repo folder** with PDF + optional supplements + optional upstream repo clone, a parallel scaffolded **vault folder** for agent-generated notes, and a `paper-info.md` metadata file written to the vault. The Acquirer subagent uses this as its authoritative schema, and downstream subagents depend on the folder structure it creates.

Paths are resolved via the helpers in `tools/paths.py` (see `.cursor/rules/paperlab-config-bootstrap.mdc`). Never hard-code paths.

## Scope boundaries

- Acquirer may read project files, search the workspace, use shell commands for git/download operations, and fetch paper or publisher landing pages for PDF download, repo detection, and supplement detection.
- Acquirer does NOT modify files inside `repo_upstream_dir(slug)` after
  cloning.
- Acquirer does NOT produce spec.md, code_map.md, or any other agent's
  artifacts.
- Acquirer does NOT process or extract content from downloaded PDFs —
  it only downloads them. Extraction is the Dissector subagent's job.
- Acquirer reads the main PDF's text ONLY for repo URL detection. It
  does not extract or record any other content from the PDF.

## Conventions

- **Naming**:
  - `<slug>` is user-provided; Acquirer subagent does not invent it. Do not change the <slug> such as capitalize or decapitalize the letters, use as user input.
  - Main PDF: `<slug>.pdf`
- Supplement PDFs produced during acquisition if supplemental materials are available:
    - Single supplement → `<slug>_supplement.pdf`
    - Multiple supplements → `<slug>_supplement1.pdf`,
      `<slug>_supplement2.pdf`, etc., in landing-page order
  - Dissector subagent recognizes both patterns.

- **Structure**: Acquirer subagent creates two parallel folders for each paper:
  - **Repo side** — `repo_paper_dir(slug)` holds the PDF (`<slug>.pdf`), `supplementals/` (if any), and `upstream/<slug>/` (if a git repo exists).
  - **Vault side** — `vault_slug_dir(slug)` is created empty for downstream subagents to fill with `spec.md`, `code_map.md`, etc.
  The `paper-info.md` file is written to the **vault** folder (`vault_path(slug, "paper-info.md")`) and links back to the repo-side PDF and upstream paths using absolute paths from `tools/paths.py`.
- **Idempotency**: Acquirer subagent uses a state-driven checklist (see §3).
  Each item is checked before attempting. Items already done are
  marked "done (previously)" and skipped. If everything is already
  complete, Acquirer subagent writes an updated `paper-info.md` reporting full
  completion and reports "nothing to do" — no refusal.

- **Two modes**: `acquire <slug> <url>` (new paper) and `rerun <slug>`
  (refresh an existing paper). `rerun` runs the same checklist but is
  explicitly for papers already in the workspace: it downloads only
  what is still missing, refreshes derived metadata (commit SHA,
  repo-URL re-scan), and **regenerates `paper-info.md` against the
  current schema**. `rerun` requires the paper to already exist (repo
  or vault folder present); otherwise it directs the user to
  `acquire`. `rerun` carries implicit replace authorization for
  `paper-info.md` (overwrite without prompting, warn in the report) —
  see `.cursor/rules/paperlab-regenerate-prompt.mdc`.

- **Auto-dissect handoff**: acquisition is a single user action. When
  the run finishes **with the main PDF present**, the Acquirer invokes
  the Dissector subagent for `<slug>` automatically — no user
  confirmation, no "next step" instruction. The PDF is the only gating
  item; missing supplements or a missing upstream repo are
  non-blocking and do not prevent the dissect. If the dissect
  overwrites an existing `spec.md`, that is allowed under the same
  regenerate-prompt exception (overwrite + warn).

- **PDF-missing branch**: when the main PDF could not be downloaded
  (paywall, auth, network), the Acquirer does NOT run the Dissector.
  It surfaces an interactive prompt (`AskQuestion`) telling the user
  the exact target path (`repo_pdf_path(slug)`) and source URL and
  asking them to place the PDF and re-run, then ends the turn.

- Each landing-page fetch attempt has a reasonable timeout. If a supplement URL doesn't respond, skip it and continue; do not retry.

- Before downloading a candidate supplement PDF, verify the URL ends in
  `.pdf` (case-insensitive). Skip non-PDF supplements even if they
  appear in the supplement section.
- If a PDF is larger than 100 MB, skip and report: "Supplement at <URL>
  exceeds 100 MB; download manually if needed."

- Deduplicate supplement URLs before downloading. If the same URL
  appears multiple times, download once.

## Required outputs

### 1. Folder structure

Each acquisition creates two parallel folders: one in the repo for source material, one in the vault for generated notes.

For example, GEARS is the slug name.

**Repo side** (`repo_paper_dir("GEARS")`):

```
<repo>/papers/GEARS/
├── GEARS.pdf                 ← downloaded by Acquirer
├── supplementals/            ← created by Acquirer if any supplements found
│   ├── GEARS_supplement.pdf
│   └── ...
└── upstream/                 ← created by Acquirer if a git repo is found
    └── GEARS/                ← cloned by Acquirer
```

**Vault side** (`vault_slug_dir("GEARS")`):

```
<vault>/GEARS/
└── paper-info.md             ← written by Acquirer

Files added later by other subagents (not shown above):
- spec.md            by the Dissector subagent
- code_map.md        by the Implementer subagent
- <concept>.md       by the Explainer subagent
- critic_reviews.md  by the Critic subagent
- notes.md           by the user
```

Both folders must exist before downstream subagents run.

### 2. paper-info.md format

Write `paper-info.md` to `vault_path(slug, "paper-info.md")`. Use absolute paths (built via `tools/paths.py`) when referencing repo-side files so the links are clickable from Obsidian. Template:

```markdown
---
paper: <slug>
category: model
agent: acquirer
tags:
- AI-guided-paper-reading
- paper-acquisition
---

# <slug>

**Source URL:** <URL provided by user>
**Acquired:** MM/DD/YYYY

## Files

| Item | Status | Absolute path / Notes |
|------|--------|-----------------------|
| Main PDF | ✓ done / ⏳ pending | absolute path from `repo_pdf_path(slug)` or "manual download required" |
| Supplement PDFs | ✓ (N found) / — none detected / ⏳ pending | absolute path of `repo_supplementals_dir(slug)` + filenames |
| Upstream repo | ✓ cloned / ⏳ pending / ✗ not found | absolute path of `repo_upstream_dir(slug)`, URL, and commit SHA |

## Pending actions

<list each pending item with instructions. If none, "none">

## Acquisition notes

<warnings, partial failures, sources used for repo detection, etc.>

```
Acquisition notes should also capture any disclaimers or limitations of the cloned repo that the Acquirer subagent encountered while scanning the PDF. (e.g., 'some data/models noted in paper are not in the public repo'). This informs downstream agents that coverage may be incomplete.

### 3. Acquisition policy

Acquirer subagent operates on a **state-driven checklist**. For each required
item, Acquirer subagent checks the current state and attempts to provide the
item if missing. Each item is independent — one failure does not
prevent attempts on others.

**The checklist** (all paths resolved via `tools/paths.py`):

1. Repo folder (`repo_paper_dir(slug)`)
2. Vault folder (`vault_slug_dir(slug)`)
3. Main PDF (`repo_pdf_path(slug)`)
4. Supplement PDFs (`repo_supplementals_dir(slug)/<slug>_supplement*.pdf`)
5. Git repo URL (determined from PDF, landing page, or user argument)
6. Git repo clone (`repo_upstream_dir(slug)`)
7. Commit SHA (captured after clone)
8. paper-info.md (written last to `vault_path(slug, "paper-info.md")`, summarizing state)

**Per-item behavior:**

**Item 1: Repo folder**
- If `repo_paper_dir(slug)` exists → mark "done," skip creation.
- If missing → create it, mark "done."
- Never fails.
- **CRITICAL: Once created, this folder must NOT be removed during the run, regardless of whether other items succeed or fail.**

**Item 2: Vault folder**
- If `vault_slug_dir(slug)` exists → mark "done," skip creation.
- If missing → create it, mark "done."
- Never fails.
- This is where `paper-info.md` (Item 8) and all downstream artifacts live.

**Item 3: Main PDF**
- If `repo_pdf_path(slug)` already exists → mark "done."
- Otherwise, attempt download per publisher rules (§ PDF download below) and save to `repo_pdf_path(slug)`.
- If download succeeds → mark "done."
- If download fails → mark "pending manual download," record failure reason in Acquisition notes. Do NOT abort the run.

**Item 4: Supplement PDFs**
- If any `<slug>_supplement*.pdf` files already exist under `repo_supplementals_dir(slug)` → mark "done (manual or previous run)."
- Otherwise, create `repo_supplementals_dir(slug)` if needed, then attempt landing-page scrape per publisher rules (§ Supplement handling below).
- If scrape succeeds and supplements found → download each into `repo_supplementals_dir(slug)`, mark "done."
- If scrape fails or finds none → mark "none detected" or "pending manual download," depending on whether the scrape itself worked.

**Item 5: Git repo URL**
- If `--repo <url>` provided → use that directly, mark "done."
- Else, try sources in order:
  - (a) Main PDF text (if PDF exists from item 3)
  - (b) Landing page HTML (if reachable from item 4)
- If exactly one URL found → mark "done" with source noted.
- If multiple URLs found → list them to user and ask which to clone ("clone URL-1," "clone all," or "skip"). Do not guess. End turn; user's response re-invokes the checklist from Item 6.
- If no URL found → mark "unknown." User can re-invoke with `--repo <url>`.

**Item 6: Git repo clone**
- Requires item 5 to have produced a URL.
- If `repo_upstream_dir(slug)` already exists and contains `.git/` → mark "done (previously cloned)."
- Else, run `git clone <url> "$(python -m tools.paths upstream <slug>)"`.
- If clone succeeds → mark "done."
- If clone fails → mark "failed," record error in Acquisition notes.

**Item 7: Commit SHA**
- Requires item 6 to have succeeded (or the repo to already exist).
- Run `git -C "$(python -m tools.paths upstream <slug>)" rev-parse HEAD`.
- Record in `paper-info.md`.

**Item 8: paper-info.md**
- Always written to `vault_path(slug, "paper-info.md")`, summarizing the state of all prior items.
- Includes an explicit "Pending actions" section listing any items marked "pending manual" or "unknown."
- Never fails — this is the final step that leaves the user informed.

### 4. Reference rules

These rules are cited by checklist items above. They are reference
material, not a separate sequence of steps.

#### PDF download rules (Item 3)

- If the URL is a direct PDF link, attempt download with available download or fetch tooling. Verify the response is actually a PDF (starts with `%PDF-`) and not HTML.
- If the URL is a landing page, attempt to find the PDF link on that
  page and follow it.
- Known paywalled publishers (Nature, Elsevier/ScienceDirect, Wiley,
  Springer non-open-access, Cell family) will typically require
  authentication and fail. On failure, mark Item 3 as "pending manual
  download" and continue with the rest of the checklist.
- IMPORTANT: if PDF download returns HTML (check first bytes for
  `%PDF-` vs `<!DOC`), delete the bogus file but do NOT delete the
  folder. Mark Item 3 as pending and continue.

#### Supplement publisher rules (Item 4)

The Acquirer subagent fetches the user-provided URL to retrieve the landing page HTML, then identifies supplements using publisher-specific rules:

- **arXiv** (`arxiv.org`): check for "Ancillary files"; download each
  file ending in `.pdf`.
- **bioRxiv / medRxiv** (`biorxiv.org`, `medrxiv.org`): find
  "Supplementary Material" section; download each linked `.pdf`.
- **Nature family** (`nature.com`): find "Supplementary Information";
  download `MOESM<N>_ESM.pdf` files. If landing page is auth-gated,
  mark Item 4 as pending manual download.
- **Cell family** (`cell.com`, `sciencedirect.com`): find "Supplemental
  Information"; download `mmc<N>.pdf` or "Document S<N>" linked PDFs.
- **Open publishers** (PLOS, eLife, Frontiers): find "Supporting
  Information" or "Supplementary Material"; download all linked PDFs.
- **Unknown publishers (fallback)**: scan all `<a href>` links whose
  visible text or URL contains "supplement", "supporting", "extended",
  "appendix", "SI" (case-insensitive) AND whose URL ends in `.pdf`.

Naming (all under `repo_supplementals_dir(slug)`):
- Zero supplements found → no file created.
- One supplement → save as `<slug>_supplement.pdf`.
- Multiple supplements → save as `<slug>_supplement1.pdf`,
  `<slug>_supplement2.pdf`, etc., in landing-page order.

Per-supplement failure: a supplement URL returning 404/403/empty →
log the failure; continue with remaining supplements. Does not affect
any other checklist item.

#### Repo detection sources (Item 5)

URL patterns to match in any scanned text:
- `github.com/<owner>/<repo>`
- `gitlab.com/<owner>/<repo>`
- `bitbucket.org/<owner>/<repo>`
- `codeocean.com/capsule/<id>`
- `zenodo.org/record/<id>`

Priority order when searching:
1. `--repo <url>` argument (if provided, use directly; skip scanning)
2. Main PDF text (only if Item 3 produced a PDF)
3. Landing page HTML (only if Item 4's landing-page fetch succeeded)

Multiple matches from PDF + landing page → deduplicate by URL, then
present to user.

#### Repo clone rules (Item 6)

- Resolve the destination: `DEST="$(python -m tools.paths upstream <slug>)"`.
  Note: this destination uses `<slug>` as the inner directory name regardless of the upstream repo's own name.
- Clone command: `git clone <url> "$DEST"`.
- If clone succeeds, proceed to Item 7.
- If clone fails (private repo, 404, network error, auth required),
  mark Item 6 as "failed," record the error message in Acquisition
  notes. Do NOT remove the folder or any other acquired assets.

#### Commit capture (Item 7)

- After successful clone, run:
  `git -C "$(python -m tools.paths upstream <slug>)" rev-parse HEAD`.
- Record the 40-char SHA in `paper-info.md`.
- If the repo was cloned in a previous run (directory already exists
  with `.git/`), still run rev-parse to refresh the SHA.