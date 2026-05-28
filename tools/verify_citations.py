"""Citation verifier for PaperLab vault markdown.

Detects citations in a markdown file (or stdin draft), resolves them through
three tiers (arXiv API → Crossref API → firecrawl CLI fallback), parses any
nearby claimed metadata, and emits a JSON report consumed by the
``citation-verifier`` subagent and the post-hoc hook.

Status semantics
----------------
- ``verified``   : resolver returned metadata; all claimed fields (when
                   present) match. PASS.
- ``mismatched`` : resolved, but at least one claimed field disagrees.
                   FAIL — only state that flips the exit code to 1.
- ``unresolved`` : all resolvers failed (network, 404, firecrawl miss).
                   Reported as a warning; does not fail the gate, because
                   transient resolver failure (proxy, rate limit, quota)
                   is common for valid citations.
- ``skipped``    : malformed ID, placeholder, or unsupported scheme.
                   Informational only.

Cache
-----
Per-paper cache at ``papers/<slug>/.cache/citations/<sha1(kind,id)>.json``.
Cache stores only resolver output, not claimed fields. Tutor session end
clears the directory (handled by the tutor subagent, not this tool).

CLI
---
::

    python -m tools.verify_citations --file <path> --slug <slug> [--json]
    python -m tools.verify_citations --stdin --slug <slug> [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from tools.paths import firecrawl_cli, repo_paper_dir


ARXIV_RE = re.compile(
    r"""
    (?:arXiv:\s*|arxiv\.org/(?:abs|pdf)/)
    (?P<id>\d{4}\.\d{4,5})(?:v\d+)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

DOI_RE = re.compile(
    r"""
    \b(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?
    (?P<id>10\.\d{4,9}/[-._;()/:A-Z0-9]+)
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

URL_RE = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)

CLAIMED_AUTHOR_YEAR_RE = re.compile(
    r"""
    (?P<authors>[A-Z][A-Za-z\-]+(?:\s+(?:et\s+al\.?|and\s+[A-Z][A-Za-z\-]+))?)
    [\s,]+
    (?P<year>(?:19|20)\d{2})
    """,
    re.VERBOSE,
)

MD_LINK_RE = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<url>[^)]+)\)")

ARXIV_PLACEHOLDER_RE = re.compile(
    r"(?:arXiv:\s*)(?P<id>X{4,}\.X{4,})", re.IGNORECASE
)


@dataclass
class Claimed:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None


@dataclass
class Resolved:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None


@dataclass
class CitationRecord:
    raw: str
    kind: str
    id: str
    line: int
    claimed: Claimed
    resolved: Resolved
    status: str
    source: str
    notes: str = ""


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _cache_dir(slug: str) -> Path:
    d = repo_paper_dir(slug) / ".cache" / "citations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_get(slug: str, kind: str, ident: str) -> dict[str, Any] | None:
    p = _cache_dir(slug) / f"{_sha1(f'{kind}:{ident}')}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_put(slug: str, kind: str, ident: str, payload: dict[str, Any]) -> None:
    p = _cache_dir(slug) / f"{_sha1(f'{kind}:{ident}')}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _line_context(text: str, idx: int) -> str:
    """Return the current line plus the preceding line.

    Claimed-metadata hints (markdown link text, ``Author et al., YYYY``)
    must sit on the same line as the citation, or immediately above it.
    A wider window leaks neighbouring citations' metadata across records.
    """
    start = text.rfind("\n", 0, idx)
    start = 0 if start == -1 else start + 1
    prev = text.rfind("\n", 0, max(0, start - 1))
    prev_start = 0 if prev == -1 else prev + 1
    end = text.find("\n", idx)
    if end == -1:
        end = len(text)
    return text[prev_start:end]


def _parse_claimed(context: str, url_for_link: str | None = None) -> Claimed:
    """Pull title/authors/year hints from markdown around a citation.

    Looks for a markdown link whose URL matches ``url_for_link`` (title text),
    and a nearby ``Author et al., YYYY`` pattern.
    """
    claimed = Claimed()

    if url_for_link:
        for m in MD_LINK_RE.finditer(context):
            if url_for_link in m.group("url"):
                text = m.group("text").strip()
                # Skip link text that is clearly a citation key
                # ("Vaswani et al., 2017") rather than a real title.
                # A title-looking string has >= 4 tokens AND doesn't match
                # the Author-year pattern.
                if (
                    len(text.split()) >= 4
                    and not CLAIMED_AUTHOR_YEAR_RE.fullmatch(text)
                ):
                    claimed.title = text
                break

    m = CLAIMED_AUTHOR_YEAR_RE.search(context)
    if m:
        author_blob = m.group("authors").strip()
        claimed.authors = [author_blob]
        try:
            claimed.year = int(m.group("year"))
        except ValueError:
            pass

    return claimed


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def detect_citations(text: str) -> list[CitationRecord]:
    """Find all arXiv IDs, DOIs, and bare URLs in ``text``.

    Order: arXiv first (most specific), then DOI, then URLs not already
    captured by the first two. Placeholders are emitted as ``skipped``.
    """
    records: list[CitationRecord] = []
    consumed: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(not (end <= s or start >= e) for s, e in consumed)

    for m in ARXIV_PLACEHOLDER_RE.finditer(text):
        s, e = m.span()
        consumed.append((s, e))
        records.append(
            CitationRecord(
                raw=m.group(0), kind="arxiv", id=m.group("id"),
                line=_line_of(text, s), claimed=Claimed(), resolved=Resolved(),
                status="skipped", source="", notes="placeholder ID",
            )
        )

    for m in ARXIV_RE.finditer(text):
        s, e = m.span()
        if overlaps(s, e):
            continue
        consumed.append((s, e))
        ident = m.group("id")
        raw = m.group(0)
        ctx = _line_context(text, s)
        claimed = _parse_claimed(ctx, url_for_link=f"arxiv.org/abs/{ident}")
        records.append(
            CitationRecord(
                raw=raw, kind="arxiv", id=ident, line=_line_of(text, s),
                claimed=claimed, resolved=Resolved(), status="pending", source="",
            )
        )

    for m in DOI_RE.finditer(text):
        s, e = m.span()
        if overlaps(s, e):
            continue
        ident = m.group("id").rstrip(".,);")
        if not ident.startswith("10."):
            continue
        consumed.append((s, e))
        raw = m.group(0)
        ctx = _line_context(text, s)
        claimed = _parse_claimed(ctx, url_for_link=ident)
        records.append(
            CitationRecord(
                raw=raw, kind="doi", id=ident, line=_line_of(text, s),
                claimed=claimed, resolved=Resolved(), status="pending", source="",
            )
        )

    for m in URL_RE.finditer(text):
        s, e = m.span()
        if overlaps(s, e):
            continue
        consumed.append((s, e))
        url = m.group(0).rstrip(".,);]")
        ctx = _line_context(text, s)
        claimed = _parse_claimed(ctx, url_for_link=url)
        records.append(
            CitationRecord(
                raw=url, kind="url", id=url, line=_line_of(text, s),
                claimed=claimed, resolved=Resolved(), status="pending", source="",
            )
        )

    records.sort(key=lambda r: r.line)
    return records


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


_USER_AGENT = "PaperLab-citation-verifier/0.1 (https://github.com/paperlab)"


def _http_get(url: str, timeout: float = 10.0) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def resolve_arxiv(arxiv_id: str) -> Resolved | None:
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    body = _http_get(url)
    if not body:
        return None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = root.find("a:entry", ns)
    if entry is None:
        return None
    title_el = entry.find("a:title", ns)
    pub_el = entry.find("a:published", ns)
    authors = [
        (n.findtext("a:name", default="", namespaces=ns) or "").strip()
        for n in entry.findall("a:author", ns)
    ]
    title = (title_el.text or "").strip() if title_el is not None else None
    year = None
    if pub_el is not None and pub_el.text and len(pub_el.text) >= 4:
        try:
            year = int(pub_el.text[:4])
        except ValueError:
            pass
    if title is None and not authors and year is None:
        return None
    return Resolved(title=title, authors=[a for a in authors if a], year=year)


def resolve_doi(doi: str) -> Resolved | None:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}"
    body = _http_get(url)
    if not body:
        return None
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    msg = data.get("message") or {}
    title_list = msg.get("title") or []
    title = title_list[0].strip() if title_list else None
    authors_raw = msg.get("author") or []
    authors = [
        " ".join(filter(None, [a.get("given"), a.get("family")])).strip()
        for a in authors_raw
    ]
    year = None
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            try:
                year = int(parts[0][0])
                break
            except (TypeError, ValueError):
                continue
    if not title and not authors and year is None:
        return None
    return Resolved(title=title, authors=[a for a in authors if a], year=year)


def resolve_via_firecrawl(url: str) -> Resolved | None:
    """Fallback: shell out to the firecrawl CLI for a markdown scrape.

    Returns ``None`` on any failure (CLI missing, network, parse error).
    Per the locked design (Q1=raise on missing helper), this is the only
    place where firecrawl unavailability is tolerated — we degrade to
    ``unresolved`` rather than crash the whole verifier run.
    """
    try:
        cli = firecrawl_cli()
    except FileNotFoundError:
        return None

    try:
        proc = subprocess.run(
            [str(cli), "scrape", url, "--formats", "markdown"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None

    md = proc.stdout
    title = None
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break
    year_m = re.search(r"\b(19|20)\d{2}\b", md[:2000])
    year = int(year_m.group(0)) if year_m else None
    if title is None and year is None:
        return None
    return Resolved(title=title, authors=[], year=year)


# ---------------------------------------------------------------------------
# Judging
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def _title_match(claimed: str | None, resolved: str | None) -> bool:
    if not claimed or not resolved:
        return True
    c, r = _norm(claimed), _norm(resolved)
    if c == r or c in r or r in c:
        return True
    c_tokens = set(re.findall(r"[a-z0-9]+", c))
    r_tokens = set(re.findall(r"[a-z0-9]+", r))
    if not c_tokens:
        return True
    overlap = len(c_tokens & r_tokens) / max(1, len(c_tokens))
    return overlap >= 0.6


def _authors_match(claimed: list[str], resolved: list[str]) -> bool:
    if not claimed or not resolved:
        return True
    blob = _norm(" ".join(claimed))
    surnames = re.findall(r"[a-z\-]+", blob)
    if not surnames:
        return True
    resolved_blob = _norm(" ".join(resolved))
    return any(s in resolved_blob for s in surnames if len(s) > 2)


def _year_match(claimed: int | None, resolved: int | None) -> bool:
    if claimed is None or resolved is None:
        return True
    return abs(claimed - resolved) <= 1


def _judge(rec: CitationRecord) -> None:
    """Set ``status`` and ``notes`` based on claimed vs resolved fields."""
    notes: list[str] = []
    if not _title_match(rec.claimed.title, rec.resolved.title):
        notes.append(
            f"title mismatch: claimed {rec.claimed.title!r} vs resolved {rec.resolved.title!r}"
        )
    if not _authors_match(rec.claimed.authors, rec.resolved.authors):
        notes.append(
            f"authors mismatch: claimed {rec.claimed.authors} vs resolved {rec.resolved.authors}"
        )
    if not _year_match(rec.claimed.year, rec.resolved.year):
        notes.append(
            f"year mismatch: claimed {rec.claimed.year} vs resolved {rec.resolved.year}"
        )
    if notes:
        rec.status = "mismatched"
        rec.notes = "; ".join(notes)
    else:
        rec.status = "verified"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _resolve_one(rec: CitationRecord, slug: str) -> None:
    if rec.status in ("skipped",):
        return

    cached = _cache_get(slug, rec.kind, rec.id)
    if cached:
        rec.resolved = Resolved(**cached["resolved"])
        rec.source = f"cache:{cached.get('source', 'unknown')}"
        _judge(rec)
        return

    resolved: Resolved | None = None
    source = ""
    if rec.kind == "arxiv":
        resolved = resolve_arxiv(rec.id)
        source = "arxiv-api"
        if resolved is None:
            resolved = resolve_via_firecrawl(f"https://arxiv.org/abs/{rec.id}")
            source = "firecrawl"
    elif rec.kind == "doi":
        resolved = resolve_doi(rec.id)
        source = "crossref-api"
        if resolved is None:
            resolved = resolve_via_firecrawl(f"https://doi.org/{rec.id}")
            source = "firecrawl"
    elif rec.kind == "url":
        resolved = resolve_via_firecrawl(rec.id)
        source = "firecrawl"

    if resolved is None:
        rec.status = "unresolved"
        rec.source = source
        rec.notes = "all resolvers failed"
        return

    rec.resolved = resolved
    rec.source = source
    _cache_put(slug, rec.kind, rec.id, {"resolved": asdict(resolved), "source": source})
    _judge(rec)


def verify(text: str, slug: str, file_label: str = "stdin") -> dict[str, Any]:
    records = detect_citations(text)
    for rec in records:
        _resolve_one(rec, slug)

    summary = {
        "total": len(records),
        "verified": sum(1 for r in records if r.status == "verified"),
        "unresolved": sum(1 for r in records if r.status == "unresolved"),
        "mismatched": sum(1 for r in records if r.status == "mismatched"),
        "skipped": sum(1 for r in records if r.status == "skipped"),
    }
    return {
        "file": file_label,
        "slug": slug,
        "summary": summary,
        "citations": [asdict(r) for r in records],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _human_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        f"Citation verifier — {report['file']} (slug={report['slug']})",
        (
            f"  total={s['total']}  verified={s['verified']}  "
            f"mismatched={s['mismatched']}  unresolved={s['unresolved']}  "
            f"skipped={s['skipped']}"
        ),
    ]
    for c in report["citations"]:
        marker = {
            "verified": "OK",
            "mismatched": "!!",
            "unresolved": "??",
            "skipped": "--",
        }.get(c["status"], "??")
        line = (
            f"  [{marker}] line {c['line']:>4}  {c['kind']}:{c['id']}  "
            f"source={c['source'] or '-'}"
        )
        if c["notes"]:
            line += f"\n         {c['notes']}"
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    p = argparse.ArgumentParser(description="PaperLab citation verifier")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="markdown file to verify")
    src.add_argument("--stdin", action="store_true", help="read draft from stdin")
    p.add_argument("--slug", required=True, help="paper slug (for per-paper cache)")
    p.add_argument("--json", action="store_true", help="emit JSON instead of human text")
    args = p.parse_args(argv)

    if args.stdin:
        text = sys.stdin.read()
        label = "stdin"
    else:
        text = args.file.read_text(encoding="utf-8")
        label = str(args.file)

    report = verify(text, args.slug, file_label=label)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_human_report(report))

    if report["summary"]["mismatched"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
