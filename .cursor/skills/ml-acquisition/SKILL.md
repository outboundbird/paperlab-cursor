---
name: ml-acquisition
description: Sets up a PaperLab paper folder by acquiring source materials: paper PDF, optional supplements, optional upstream repository clone, commit SHA, and paper-info.md. Use when acquiring, adding, initializing, downloading, or setting up an ML paper under papers/<slug>/.
---

# ML Acquisition Schema

## Purpose

This file defines the PaperLab acquisition protocol: a scaffolded paper folder with PDF, optional upstream repo clone, and a `paper-info.md` metadata file. The Acquirer subagent uses this as its authoritative schema, and downstream subagents depend on the folder structure it creates.

## Scope boundaries

- Acquirer may read project files, search the workspace, use shell commands for git/download operations, and fetch paper or publisher landing pages for PDF download, repo detection, and supplement detection.
- Acquirer does NOT modify files inside `upstream/<repo-name>/` after
  cloning.
- Acquirer does NOT produce spec.md, code_map.md, or any other agent's
  artifacts.
- Acquirer does NOT process or extract content from downloaded PDFs —
  it only downloads them. Extraction is the Dissector subagent's job.
- Acquirer reads the main PDF's text ONLY for repo URL detection. It
  does not extract or record any other content from the PDF.

## Conventions

- **Naming**:
  - `<slug>` is user-provided; Acquirer subagent does not invent it.
  - Main PDF: `<slug>.pdf`
- Supplement PDFs produced during acquisition if supplemental materials are available:
    - Single supplement → `<slug>_supplement.pdf`
    - Multiple supplements → `<slug>_supplement1.pdf`,
      `<slug>_supplement2.pdf`, etc., in landing-page order
  - Dissector subagent recognizes both patterns.

- **Structure**: Acquirer subagent will create a folder named after the slug under `papers/`. The PDF file will be renamed as `<slug>.pdf`. If the git repo exists, Acquirer subagent will create a subfolder named `upstream/` and clone the repo there. The `paper-info.md` file will be created in the slug folder.
- **Idempotency**: Acquirer subagent uses a state-driven checklist (see §3).
  Each item is checked before attempting. Items already done are
  marked "done (previously)" and skipped. If everything is already
  complete, Acquirer subagent writes an updated `paper-info.md` reporting full
  completion and reports "nothing to do" — no refusal.

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

Under the papers/ folder, each acquisition will create a <slug> folder. Under the <slug> folder, the fetched paper PDF and supplemental material will be stored. Acquirer will create a upstream/ folder under <slug>/ for git cloning the repo, if available.

for example, GEARS is the slug name.

```bash
After Acquirer runs, papers/<slug>/ contains:

papers/GEARS/
├── GEARS.pdf              ← downloaded by Acquirer
├── paper-info.md          ← written by Acquirer
└── upstream/              ← created by Acquirer (if repo found)
    └── GEARS/             ← cloned by Acquirer

Files added later by other agents (not shown above):
Files added later by other subagents (not shown above):
- `spec.md` by the Dissector subagent
- `code_map.md` by the Implementer subagent
- `<concept>.md` by the Explainer subagent
- `critic_reviews.md` by the Critic subagent
- `<slug>_supplement.pdf` (added manually by user, if needed)
```

### 2. paper-info.md format

Provide general information of the paper and write to the `paper-info.md` file using the template below:

```markdown
---
category: model
tags:
- AI-guided-paper-reading
- paper-acquisition
---

# <slug>

**Source URL:** <URL provided by user>
**Acquired:** MM/DD/YYYY

## Files

| Item | Status | Location / Notes |
|------|--------|------------------|
| Main PDF | ✓ done / ⏳ pending | `<slug>.pdf` or "manual download required" |
| Supplement PDFs | ✓ (N found) / — none detected / ⏳ pending | list of filenames |
| Upstream repo | ✓ cloned / ⏳ pending / ✗ not found | URL and commit SHA |

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

**The checklist:**

1. Paper folder (`papers/<slug>/`)
2. Main PDF (`papers/<slug>/<slug>.pdf`)
3. Supplement PDFs (`papers/<slug>/<slug>_supplement*.pdf`)
4. Git repo URL (determined from PDF, landing page, or user argument)
5. Git repo clone (`papers/<slug>/upstream/<repo-name>/`)
6. Commit SHA (captured after clone)
7. paper-info.md (written last, summarizing state)

**Per-item behavior:**

**Item 1: Paper folder**
- If `papers/<slug>/` exists → mark "done," skip creation
- If missing → `mkdir papers/<slug>/`, mark "done"
- Never fails
- **CRITICAL: Once created, this folder must NOT be removed during the
  run, regardless of whether other items succeed or fail. Acquirer
  writes paper-info.md into this folder at the end of the run to
  report partial success. Removing the folder destroys the state
  record the user needs.**

**Item 2: Main PDF**
- If `papers/<slug>/<slug>.pdf` already exists → mark "done"
- Otherwise, attempt download per publisher rules (§ PDF download below)
- If download succeeds → mark "done"
- If download fails → mark "pending manual download," record failure
  reason in Acquisition notes. Do NOT abort the run.

**Item 3: Supplement PDFs**
- If any `<slug>_supplement*.pdf` files already exist → mark "done
  (manual or previous run)"
- Otherwise, attempt landing-page scrape per publisher rules (§
  Supplement handling below)
- If scrape succeeds and supplements found → download each, mark "done"
- If scrape fails or finds none → mark "none detected" or "pending
  manual download," depending on whether the scrape itself worked

**Item 4: Git repo URL**
- If `--repo <url>` provided → use that directly, mark "done"
- Else, try sources in order:
  - (a) Main PDF text (if PDF exists from item 2)
  - (b) Landing page HTML (if reachable from item 3)
- If exactly one URL found → mark "done" with source noted
- If multiple URLs found → list them to user and ask which to clone
  ("clone URL-1," "clone all," or "skip"). Do not guess. End turn;
  user's response re-invokes the checklist from Item 5.
- If no URL found → mark "unknown." User can re-invoke with
  `--repo <url>`.

**Item 5: Git repo clone**
- Requires item 4 to have produced a URL.
- If `papers/<slug>/upstream/<repo-name>/` already exists and contains
  `.git/` → mark "done (previously cloned)"
- Else, run `git clone <url> papers/<slug>/upstream/<repo-name>/`
- If clone succeeds → mark "done"
- If clone fails → mark "failed," record error in Acquisition notes

**Item 6: Commit SHA**
- Requires item 5 to have succeeded (or the repo to already exist).
- Run `git -C papers/<slug>/upstream/<repo-name> rev-parse HEAD`
- Record in paper-info.md

**Item 7: paper-info.md**
- Always written, summarizing the state of all prior items
- Includes an explicit "Pending actions" section listing any items
  marked "pending manual" or "unknown"
- Never fails — this is the final step that leaves the user informed

### 4. Reference rules

These rules are cited by checklist items above. They are reference
material, not a separate sequence of steps.

#### PDF download rules (Item 2)

- If the URL is a direct PDF link, attempt download with available download or fetch tooling. Verify the response is actually a PDF (starts with `%PDF-`) and not HTML.
- If the URL is a landing page, attempt to find the PDF link on that
  page and follow it.
- Known paywalled publishers (Nature, Elsevier/ScienceDirect, Wiley,
  Springer non-open-access, Cell family) will typically require
  authentication and fail. On failure, mark Item 2 as "pending manual
  download" and continue with the rest of the checklist.
- IMPORTANT: if PDF download returns HTML (check first bytes for
  `%PDF-` vs `<!DOC`), delete the bogus file but do NOT delete the
  folder. Mark Item 2 as pending and continue.

#### Supplement publisher rules (Item 3)

The Acquirer subagent fetches the user-provided URL to retrieve the landing page HTML, then identifies supplements using publisher-specific rules:

- **arXiv** (`arxiv.org`): check for "Ancillary files"; download each
  file ending in `.pdf`.
- **bioRxiv / medRxiv** (`biorxiv.org`, `medrxiv.org`): find
  "Supplementary Material" section; download each linked `.pdf`.
- **Nature family** (`nature.com`): find "Supplementary Information";
  download `MOESM<N>_ESM.pdf` files. If landing page is auth-gated,
  mark Item 3 as pending manual download.
- **Cell family** (`cell.com`, `sciencedirect.com`): find "Supplemental
  Information"; download `mmc<N>.pdf` or "Document S<N>" linked PDFs.
- **Open publishers** (PLOS, eLife, Frontiers): find "Supporting
  Information" or "Supplementary Material"; download all linked PDFs.
- **Unknown publishers (fallback)**: scan all `<a href>` links whose
  visible text or URL contains "supplement", "supporting", "extended",
  "appendix", "SI" (case-insensitive) AND whose URL ends in `.pdf`.

Naming:
- Zero supplements found → no file created.
- One supplement → save as `papers/<slug>/<slug>_supplement.pdf`.
- Multiple supplements → save as `<slug>_supplement1.pdf`,
  `<slug>_supplement2.pdf`, etc., in landing-page order.

Per-supplement failure: a supplement URL returning 404/403/empty →
log the failure; continue with remaining supplements. Does not affect
any other checklist item.

#### Repo detection sources (Item 4)

URL patterns to match in any scanned text:
- `github.com/<owner>/<repo>`
- `gitlab.com/<owner>/<repo>`
- `bitbucket.org/<owner>/<repo>`
- `codeocean.com/capsule/<id>`
- `zenodo.org/record/<id>`

Priority order when searching:
1. `--repo <url>` argument (if provided, use directly; skip scanning)
2. Main PDF text (only if Item 2 produced a PDF)
3. Landing page HTML (only if Item 3's landing-page fetch succeeded)

Multiple matches from PDF + landing page → deduplicate by URL, then
present to user.

#### Repo clone rules (Item 5)

- Clone command: `git clone <url> papers/<slug>/upstream/<repo-name>/`
  where `<repo-name>` is the last path segment of the repo URL.
- If clone succeeds, proceed to Item 6.
- If clone fails (private repo, 404, network error, auth required),
  mark Item 5 as "failed," record the error message in Acquisition
  notes. Do NOT remove the folder or any other acquired assets.

#### Commit capture (Item 6)

- After successful clone, run:
  `git -C papers/<slug>/upstream/<repo-name>/ rev-parse HEAD`
- Record the 40-char SHA in paper-info.md.
- If the repo was cloned in a previous run (directory already exists
  with `.git/`), still run rev-parse to refresh the SHA.