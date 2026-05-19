"""Figure & table discovery and extraction for PaperLab.

The Visualizer subagent uses this module to embed the paper's *own* figures
in slides instead of inventing substitute Mermaid diagrams. The Dissector
uses it to populate the §4.5 Figures & Tables section of ``spec.md``.

Strategy
--------
- :func:`list_figures` parses caption lines (``Figure N: ...`` and
  ``Table N: ...``) from each page of the PDF using ``pypdf``. No image
  data is touched at this stage — cheap and offline.
- :func:`extract_figure` renders the full page containing a given figure or
  table as a PNG using ``pymupdf`` (``fitz``). The whole-page render is
  intentional: it preserves the paper's caption verbatim, which is the
  reader's anchor when the figure is embedded in a slide. Higher fidelity
  (caption-aware bbox cropping) is out of scope for this MVP.

Cache layout
------------
Page renders are cached under
``papers/<slug>/.cache/figures/figure<N>.png`` (or ``tableN.png``).
The ``papers/`` tree is git-ignored, matching the convention already used by
``tools.pdf``.

Examples
--------
>>> from tools.figures import list_figures, extract_figure
>>> for c in list_figures("WorldModel")[:3]:
...     print(c.kind, c.number, c.page, c.caption[:40])
Figure 1 1 A World Models agent receives observatio
Figure 4 5 Flow diagram of V, M, C interaction dur
Table 1 7 Car Racing scores across baselines.
>>> extract_figure("WorldModel", "Figure", 4)
PosixPath('.../papers/WorldModel/.cache/figures/figure4.png')
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tools.paths import repo_paper_dir, repo_pdf_path


CAPTION_RE = re.compile(
    r"^\s*(Figure|Fig\.|Table)\s+(\d+)\s*[:.\u2014\u2013\-]\s*(.+)$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Caption:
    """One figure or table caption discovered in a paper PDF.

    Attributes
    ----------
    kind : str
        Either ``"Figure"`` or ``"Table"`` (normalized; ``"Fig."`` collapses
        to ``"Figure"``).
    number : int
        Caption number as printed in the paper.
    caption : str
        First sentence of the caption text, trimmed to 200 characters.
    page : int
        1-based page number where the caption was found.
    """

    kind: str
    number: int
    caption: str
    page: int


def figures_cache_dir(slug: str) -> Path:
    """``<repo>/papers/<slug>/.cache/figures/`` — cache for extracted PNGs."""
    return repo_paper_dir(slug) / ".cache" / "figures"


def _normalize_kind(raw: str) -> str:
    return "Table" if raw.strip().lower().startswith("table") else "Figure"


def _trim_to_first_sentence(text: str, max_chars: int = 200) -> str:
    text = text.strip()
    first = re.split(r"(?<=[\.!?])\s", text, maxsplit=1)[0]
    if len(first) > max_chars:
        first = first[:max_chars].rstrip() + "..."
    return first


def list_figures(slug: str, pdf_path: Path | None = None) -> list[Caption]:
    """Discover every figure and table caption in a paper PDF.

    Walks each page with ``pypdf`` and matches caption lines. Duplicates
    (same kind + number) keep their first occurrence.

    Parameters
    ----------
    slug : str
        Paper slug. Used to resolve the default PDF location.
    pdf_path : Path, optional
        Explicit PDF path. Defaults to ``repo_pdf_path(slug)``.

    Returns
    -------
    list[Caption]
        Sorted by (kind, number).

    Raises
    ------
    FileNotFoundError
        If the PDF does not exist.
    """
    from pypdf import PdfReader

    pdf = (pdf_path or repo_pdf_path(slug)).resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    reader = PdfReader(str(pdf))
    seen: set[tuple[str, int]] = set()
    out: list[Caption] = []
    for page_idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for m in CAPTION_RE.finditer(text):
            kind = _normalize_kind(m.group(1))
            num = int(m.group(2))
            key = (kind, num)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                Caption(
                    kind=kind,
                    number=num,
                    caption=_trim_to_first_sentence(m.group(3)),
                    page=page_idx,
                )
            )
    out.sort(key=lambda c: (c.kind, c.number))
    return out


def extract_figure(
    slug: str,
    kind: str,
    number: int,
    pdf_path: Path | None = None,
    *,
    dpi: int = 150,
    refresh: bool = False,
) -> Path:
    """Render the page containing a figure or table as a PNG.

    The entire page is rendered — including the caption — so the reader
    sees the figure exactly as the authors drew it. Caption-aware bbox
    cropping is intentionally out of scope; the slide's right column
    already provides extra context.

    Parameters
    ----------
    slug : str
        Paper slug. Used to resolve the default PDF location.
    kind : str
        ``"Figure"`` or ``"Table"`` (case-insensitive).
    number : int
        Caption number to extract.
    pdf_path : Path, optional
        Explicit PDF path. Defaults to ``repo_pdf_path(slug)``.
    dpi : int
        Render resolution. 150 dpi gives slide-quality output without
        bloating the cache.
    refresh : bool
        If ``True``, re-render even when a cached PNG exists.

    Returns
    -------
    Path
        Absolute path to the cached PNG.

    Raises
    ------
    FileNotFoundError
        If the PDF does not exist.
    LookupError
        If ``list_figures`` does not find a matching caption.
    RuntimeError
        If ``pymupdf`` is not installed.
    """
    kind_n = _normalize_kind(kind)
    captions = list_figures(slug, pdf_path=pdf_path)
    match = next(
        (c for c in captions if c.kind == kind_n and c.number == number),
        None,
    )
    if match is None:
        raise LookupError(
            f"{kind_n} {number} not found in {slug}. "
            f"Available: {[(c.kind, c.number) for c in captions]}"
        )

    cache = figures_cache_dir(slug) / f"{kind_n.lower()}{number}.png"
    if cache.is_file() and not refresh:
        return cache

    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise RuntimeError(
            "PyMuPDF is required for figure extraction. "
            "Install via `pip install pymupdf`."
        ) from e

    pdf = (pdf_path or repo_pdf_path(slug)).resolve()
    doc = fitz.open(str(pdf))
    try:
        page = doc[match.page - 1]
        pix = page.get_pixmap(dpi=dpi)
        cache.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(cache))
    finally:
        doc.close()
    return cache


def _cli() -> None:
    """Command-line interface.

    Usage::

        python -m tools.figures list <slug>
        python -m tools.figures extract <slug> <kind> <number> [--dpi N] [--refresh]
    """
    import argparse
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(prog="python -m tools.figures")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List every figure/table caption.")
    p_list.add_argument("slug")

    p_ex = sub.add_parser("extract", help="Render the page containing a figure/table.")
    p_ex.add_argument("slug")
    p_ex.add_argument("kind", choices=["Figure", "Table", "figure", "table"])
    p_ex.add_argument("number", type=int)
    p_ex.add_argument("--dpi", type=int, default=150)
    p_ex.add_argument("--refresh", action="store_true")

    args = parser.parse_args()
    if args.cmd == "list":
        for c in list_figures(args.slug):
            print(f"{c.kind} {c.number} (p.{c.page}): {c.caption}")
    elif args.cmd == "extract":
        print(
            extract_figure(
                args.slug,
                args.kind,
                args.number,
                dpi=args.dpi,
                refresh=args.refresh,
            )
        )


if __name__ == "__main__":
    _cli()
