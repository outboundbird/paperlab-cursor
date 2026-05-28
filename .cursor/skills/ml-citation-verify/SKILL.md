---
name: ml-citation-verify
description: Defines the citation verification protocol for PaperLab. Wraps `tools/verify_citations.py` (arXiv + Crossref APIs with firecrawl CLI fallback) and specifies how the Citation-Verifier subagent reports findings to its caller (Tutor or Explainer in the inline gate, or the post-hoc hook for non-gated agents). Use when verifying citations, checking arXiv IDs / DOIs / URLs, or auditing paper references in vault markdown.
---

# ML Citation Verify Schema

## Purpose

This skill defines what the **Citation-Verifier** subagent does, how it
is invoked, and the structured contract it returns to its caller. The
verifier exists to catch the citation failure modes the Tutor and
Explainer have produced in practice (hallucinated arXiv IDs,
author/year/title disagreements between claimed and resolved metadata,
URLs that do not point at the cited work) **before** they reach the
user or the vault.

The verifier is a wrapper around `tools/verify_citations.py`. The tool
does the detection, resolution, and field-matching; the subagent's job
is to invoke the tool with the right input, interpret its JSON output,
and report back in a form the calling agent can act on per-citation.

## Resolver tiers

| Tier | Citation kind | Resolver | Auth | Cost |
|---|---|---|---|---|
| 1 | `arxiv` | arXiv Atom API (`export.arxiv.org`) | None | Free |
| 1 | `doi` | Crossref REST API (`api.crossref.org`) | None | Free |
| 2 | `arxiv` / `doi` fallback | firecrawl CLI on the canonical URL | Firecrawl account | Free tier with quota; paid above quota |
| 2 | `url` (bare) | firecrawl CLI direct | Firecrawl account | Free tier with quota; paid above quota |

Tier 1 is tried first. Tier 2 only fires on tier-1 failure
(network error, 404, empty payload). Bare URLs go straight to tier 2 —
there is no structured tier-1 resolver for them.

If `firecrawl_cli()` raises `FileNotFoundError` (CLI not installed),
the tool degrades that citation to `unresolved` rather than crashing
the entire run.

## Per-paper cache

Cached at `papers/<slug>/.cache/citations/<sha1(kind:id)>.json`. The
cache key is `(kind, id)`, so the same arXiv ID across two files in
one paper folder hits the resolver exactly once. The cache is intended
to be cleared at Tutor session end (not yet implemented — see
`ROADMAP.md` "Verifier system").

The cache stores only resolver output, never the claimed fields parsed
from prose. Judgment (claimed-vs-resolved matching) runs on every
invocation against fresh prose context.

## Two invocation modes

### Mode A — verify a file on disk

For the post-hoc hook and for any agent that has already written a
markdown file and wants to re-check it.

```bash
python -m tools.verify_citations --file <path> --slug <slug> --json
```

### Mode B — verify a draft text held in memory

For the inline gate. The calling agent (Tutor or Explainer) has
drafted a response but has not emitted it yet; it passes the draft
to the Citation-Verifier subagent as a string argument. The subagent
writes that string to a temporary file or pipes it to the CLI:

```bash
python -m tools.verify_citations --stdin --slug <slug> --json < /tmp/draft.md
```

The `--slug` flag is mandatory in both modes — it scopes the cache.

## What the tool detects

| Kind | Pattern | Examples |
|---|---|---|
| `arxiv` | `arXiv:NNNN.NNNNN` or `arxiv.org/abs/NNNN.NNNNN` | `arXiv:1706.03762`, `https://arxiv.org/abs/2103.00020v2` |
| `doi` | `doi:10.NNNN/...` or `doi.org/10.NNNN/...` or bare `10.NNNN/...` | `doi:10.1038/nature14539` |
| `url` | Bare HTTP(S) URL whose span does not overlap an arXiv/DOI match | `https://distill.pub/2017/momentum/` |
| placeholder | `arXiv:XXXX.XXXXX` | emitted as `skipped` |

Placeholders (e.g. an unfilled template) are emitted with
`status=skipped` rather than dropped, so the user sees them in the
report.

## What the tool judges

For every resolved citation the tool compares claimed (from prose)
against resolved (from API/firecrawl) fields:

| Field | Match rule |
|---|---|
| title | Token-overlap ≥ 60% (case-insensitive), or substring containment |
| authors | At least one claimed surname appears in resolved author list |
| year | Within ±1 of resolved year |

A claimed field that is `None` (couldn't be parsed from prose)
**never** triggers a mismatch — only contradicted fields do. This
keeps false-positive pressure low.

### Status semantics

| Status | Meaning |
|---|---|
| `verified` | Resolver returned metadata; all claimed fields (when present) match — **PASS** |
| `mismatched` | Resolver returned metadata; at least one claimed field disagrees — **FAIL** |
| `unresolved` | All resolvers failed (network, 404, firecrawl miss) — **warning**, does not fail the gate |
| `skipped` | Placeholder ID or unsupported scheme — informational |

The gate-failing distinction matters because `unresolved` is often
caused by transient resolver issues (corporate proxy, arXiv rate
limit, firecrawl quota) that affect *valid* citations. Failing on
`unresolved` would burn retries that cannot succeed and frustrate
the user. Only `mismatched` — where the resolver explicitly
contradicts the claimed metadata — fails the gate.

## Output schema

The tool emits a single JSON object when called with `--json`:

```json
{
  "file": "<path or 'stdin'>",
  "slug": "<paper slug>",
  "summary": {
    "total": 5,
    "verified": 3,
    "mismatched": 0,
    "unresolved": 1,
    "skipped": 1
  },
  "citations": [
    {
      "raw": "arXiv:1706.03762",
      "kind": "arxiv",
      "id": "1706.03762",
      "line": 3,
      "claimed": {"title": null, "authors": ["Vaswani et al."], "year": 2017},
      "resolved": {"title": "Attention Is All You Need", "authors": ["Ashish Vaswani", "..."], "year": 2017},
      "status": "verified",
      "source": "arxiv-api",
      "notes": ""
    }
  ]
}
```

Field semantics:

- `kind`: one of `arxiv`, `doi`, `url`.
- `id`: canonical identifier (no prefix, no version suffix for arXiv).
- `line`: 1-indexed line in the source.
- `claimed`: best-effort parse from prose (current line + previous
  line). `null` / `[]` when nothing could be extracted.
- `resolved`: resolver output. Empty when `status` is `unresolved` or
  `skipped`.
- `source`: which resolver succeeded — `arxiv-api`, `crossref-api`,
  `firecrawl`, `cache:<original-source>`, or `""` for skipped.
- `notes`: human-readable explanation when `status` is `mismatched`
  or `unresolved`.

Exit code: 0 if no `mismatched` rows; 1 if any `mismatched` row.
`unresolved` and `skipped` rows do not affect the exit code.

## Subagent contract — what Citation-Verifier returns to its caller

When invoked as a subagent, the Citation-Verifier returns a structured
report the calling agent can act on without re-parsing the tool
output. The report is a single message in this shape:

```markdown
## Citation verification report

- source: <path or "draft">
- slug: <slug>
- total: <N>  verified: <V>  mismatched: <M>  unresolved: <U>  skipped: <S>

### Mismatched
- line 12, arxiv:1706.03762 — year mismatch: claimed 2016 vs resolved 2017
- line 18, doi:10.1038/nature14539 — authors mismatch: claimed [Hinton et al.] vs resolved [LeCun, Bengio, Hinton]

### Unresolved (warnings)
- line 24, url:https://example.com/some-paper — all resolvers failed

### Skipped
- line 30, arxiv:XXXX.XXXXX — placeholder ID

### Verdict
- **FAIL** (1+ mismatched)  |  **PASS** (no mismatched rows)
```

The verdict line is mandatory. The calling agent uses it as the
gate-decision signal. Only `mismatched` affects the verdict —
`unresolved` and `skipped` are reported for user awareness but do
not block emission.

## Scope boundaries

The Citation-Verifier:

- **Does not** edit any file. It is read-only.
- **Does not** invoke other subagents.
- **Does not** fetch full PDFs, abstracts, or run quote-level checks.
  Only title / authors / year of resolved records are compared.
- **Does not** judge whether a citation is *appropriate* for the
  surrounding claim. Only whether the cited record exists and matches
  the claimed metadata.
- **Does not** dedupe across line numbers. The same arXiv ID cited at
  two locations produces two report rows (with the second hitting the
  cache); both are useful to the user.

## Where this fits in the verifier system

The Citation-Verifier is one of two verifier subagents (the other is
the `latex-verifier`). Both are invoked by the inline gate in Tutor
and Explainer **before** content reaches the user, and by the
post-hoc hook on vault `*.md` writes from any future agent that does
not gate inline. The inline gate runs them sequentially —
LaTeX first, citations second — with separate retry budgets so the
logs stay clear. See `AGENTS.md` § "Verifier system" for the full
architecture.

## Self-checks (verifier subagent, at end of its turn)

- Did I report the verdict line (`PASS` or `FAIL`)?
- Did I list every `mismatched`, `unresolved`, and `skipped` row
  with the citation kind, ID, and line number intact?
- Did I propagate `notes` verbatim from the tool output?
- Did I avoid suggesting fixes the tool did not name?
- Did I avoid editing the source file?
