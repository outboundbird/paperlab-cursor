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

from tools.paths import repo_paper_dir, repo_pdf_path, vault_slug_dir


CAPTION_RE = re.compile(
    r"^\s*(Figure|Fig\.|Table)\s+(\d+)\s*[:.\u2014\u2013\-]\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
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


def captions_by_component(
    slug: str,
    component: str,
    pdf_path: Path | None = None,
) -> list[Caption]:
    """Find figures/tables whose surrounding prose mentions a given component.

    Use this for ad-hoc, user-driven retrieval ("show me every figure about
    ConvVAE") that the dissector's per-paper Role tagging doesn't address.
    Searches the full PDF text — not just captions — for paragraphs that
    reference both the component name AND a figure/table number, then returns
    the matching captions.

    Parameters
    ----------
    slug : str
        Paper slug.
    component : str
        Component name to search for (case-insensitive, whole-word match).
        Examples: ``"ConvVAE"``, ``"MDN-RNN"``, ``"controller"``, ``"V"``.
        Short single-letter names (``"V"``, ``"M"``, ``"C"``) are matched as
        whole words to avoid false positives.
    pdf_path : Path, optional
        Explicit PDF path. Defaults to ``repo_pdf_path(slug)``.

    Returns
    -------
    list[Caption]
        Captions whose prose context references the component, sorted by
        (kind, number).
    """
    from pypdf import PdfReader

    pdf = (pdf_path or repo_pdf_path(slug)).resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    captions = list_figures(slug, pdf_path=pdf)
    if not captions:
        return []

    # PDF extraction often loses paragraph boundaries, so a paragraph-based
    # splitter would trivially make the whole doc match. We use a fixed
    # character window around each component mention instead, and pull every
    # figure/table reference inside that window.
    proximity_chars = 400

    comp_re = re.compile(rf"\b{re.escape(component)}\b", re.IGNORECASE)
    fig_ref_re = re.compile(
        r"\b(Figure|Fig\.?|Table)\s+(\d+)\b",
        re.IGNORECASE,
    )

    reader = PdfReader(str(pdf))
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)

    referenced: set[tuple[str, int]] = set()
    for hit in comp_re.finditer(full_text):
        window_start = max(0, hit.start() - proximity_chars)
        window_end = min(len(full_text), hit.end() + proximity_chars)
        window = full_text[window_start:window_end]
        for m in fig_ref_re.finditer(window):
            kind = _normalize_kind(m.group(1))
            num = int(m.group(2))
            referenced.add((kind, num))

    matches = [c for c in captions if (c.kind, c.number) in referenced]
    matches.sort(key=lambda c: (c.kind, c.number))
    return matches


_PAGE_MARGIN_PX = 36       # text-area inset on left/right/top/bottom
_BBOX_PADDING_PX = 6       # gap between figure region and adjacent caption rects
_MIN_BBOX_HEIGHT_PX = 60   # below this, the candidate rect is rejected
_MIN_FIG_WIDTH_PX = 60     # below this, an x-strip is treated as a gutter
_GAP_MERGE_PX = 3.0        # text rects closer than this are merged on each axis
_COLUMN_PAD_PX = 6         # padding added around detected column x-range
_COLUMN_MIN_GUTTER_PX = 12  # minimum gutter width between columns
_LABEL_FONT_TOLERANCE = 1.5  # span > (body_size - this) counts as body text


def _find_caption_rect(page, kind: str, number: int):
    """Find the rectangle of a "Figure N" or "Table N" caption on a page.

    Uses PyMuPDF's ``page.search_for``. Returns the first hit's rect, or
    ``None`` if not found. Tries a few common spelling variants.
    """
    variants = [f"{kind} {number}:", f"{kind} {number}."]
    if kind == "Figure":
        variants += [f"Fig. {number}:", f"Fig. {number}."]
    for variant in variants:
        rects = page.search_for(variant)
        if rects:
            return rects[0]
    return None


def _find_caption_block(page, kind: str, number: int):
    """Return the full text-block rect that contains the caption.

    Unlike :func:`_find_caption_rect` which only locates the narrow
    ``Figure N:`` literal, this returns the bounding box of the entire
    caption paragraph — which spans exactly the figure's effective width
    in the layout. A narrow caption block ⇒ narrow figure (wrapped/inset);
    a full-width block ⇒ page-spanning figure. This is the layout signal
    used to choose the figure's column.
    """
    import fitz

    pat = re.compile(
        rf"^\s*(?:{kind}|Fig\.)\s+{number}\b", re.IGNORECASE
    )
    try:
        data = page.get_text("dict")
    except Exception:
        return None
    for blk in data.get("blocks", []):
        if blk.get("type", 1) != 0:
            continue
        # Join all spans in the first line — captions often render the
        # "Figure" word and the number as separate spans.
        first_line_text = ""
        for line in blk.get("lines", []):
            joined = "".join(s.get("text", "") for s in line.get("spans", []))
            if joined.strip():
                first_line_text = joined.lstrip()
                break
        if not pat.match(first_line_text):
            continue
        bbox = blk.get("bbox")
        if bbox and len(bbox) == 4:
            return fitz.Rect(*bbox)
    return None


def _body_font_size(page) -> float:
    """Estimate body-text font size on a page as the size with the most
    characters set in it. Returns 10.0 as a sane default when extraction
    fails.
    """
    sizes: dict[float, int] = {}
    try:
        data = page.get_text("dict")
    except Exception:
        return 10.0
    for blk in data.get("blocks", []):
        if blk.get("type", 1) != 0:
            continue
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                sz = round(float(span.get("size", 0.0)), 1)
                if sz <= 0:
                    continue
                sizes[sz] = sizes.get(sz, 0) + len(span.get("text", ""))
    if not sizes:
        return 10.0
    return max(sizes.items(), key=lambda kv: kv[1])[0]


def _is_paragraph_block(total_chars: int, nlines: int) -> bool:
    """Return True if a text block is shaped like a body paragraph.

    Filters out:
      * figure-internal labels (short, 1 line)
      * sub-captions like ``(a) ...`` (~20–30 chars, 1 line)
      * section headings (~20 chars, 1–2 lines)
      * **table rows** — many chars but spans are split per column, so
        PyMuPDF reports many "lines" with very few chars each.
    """
    if total_chars < 40 or nlines < 1:
        return False
    if total_chars / nlines < 10:
        return False
    return total_chars >= 80 or nlines >= 3


def _body_text_rects(page, band, min_body_size: float):
    """Body-paragraph rects (clipped to ``band``) on ``page``.

    A block qualifies only if both its font size is near body and its shape
    matches a paragraph (see :func:`_is_paragraph_block`). Figure-internal
    labels and short text snippets are skipped so they don't fragment the
    y-projection inside the figure region.
    """
    import fitz

    threshold = min_body_size - _LABEL_FONT_TOLERANCE
    try:
        data = page.get_text("dict")
    except Exception:
        return []
    out: list[fitz.Rect] = []
    for blk in data.get("blocks", []):
        if blk.get("type", 1) != 0:
            continue
        weighted_size = 0.0
        total_chars = 0
        lines = blk.get("lines", [])
        for line in lines:
            for span in line.get("spans", []):
                n = len(span.get("text", ""))
                if n == 0:
                    continue
                weighted_size += float(span.get("size", 0.0)) * n
                total_chars += n
        if total_chars == 0:
            continue
        dominant = weighted_size / total_chars
        if dominant < threshold:
            continue
        if not _is_paragraph_block(total_chars, len(lines)):
            continue
        bbox = blk.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        r = fitz.Rect(*bbox)
        if not r.intersects(band):
            continue
        clipped = r & band
        if clipped.get_area() > 0:
            out.append(clipped)
    return out


def _free_intervals(ranges, lo, hi):
    """Complement of occupied 1D intervals inside ``[lo, hi]``.

    Adjacent intervals separated by less than ``_GAP_MERGE_PX`` are merged
    first so that anti-aliased text doesn't fragment the figure region into
    a thousand slivers.
    """
    if hi <= lo:
        return []
    if not ranges:
        return [(lo, hi)]
    rs = sorted((max(lo, s), min(hi, e)) for s, e in ranges if e > lo and s < hi)
    if not rs:
        return [(lo, hi)]
    merged: list[list[float]] = [list(rs[0])]
    for s, e in rs[1:]:
        if s <= merged[-1][1] + _GAP_MERGE_PX:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    free: list[tuple[float, float]] = []
    cursor = lo
    for s, e in merged:
        if s > cursor:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < hi:
        free.append((cursor, hi))
    return free


def _page_columns(page, body_size: float) -> list[tuple[float, float]]:
    """Detect the page's text columns from substantial body-paragraph runs.

    Only blocks that look like real prose (>= 80 chars or >= 3 text lines)
    contribute to column detection — this excludes page headers, footers,
    and short captions that often straddle the column gutter and would
    otherwise merge two columns into one.

    Returns a list of ``(x0, x1)`` column ranges, or a single full-width
    column when no qualifying blocks are found.
    """
    threshold = body_size - _LABEL_FONT_TOLERANCE
    full_x0 = page.rect.x0 + _PAGE_MARGIN_PX
    full_x1 = page.rect.x1 - _PAGE_MARGIN_PX

    try:
        data = page.get_text("dict")
    except Exception:
        return [(full_x0, full_x1)]

    paragraph_ranges: list[tuple[float, float]] = []
    for blk in data.get("blocks", []):
        if blk.get("type", 1) != 0:
            continue
        weighted_size = 0.0
        total_chars = 0
        lines = blk.get("lines", [])
        for line in lines:
            for span in line.get("spans", []):
                n = len(span.get("text", ""))
                if n == 0:
                    continue
                weighted_size += float(span.get("size", 0.0)) * n
                total_chars += n
        if total_chars == 0:
            continue
        dominant = weighted_size / total_chars
        if dominant < threshold:
            continue
        if not _is_paragraph_block(total_chars, len(lines)):
            continue
        bbox = blk.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        paragraph_ranges.append((float(bbox[0]), float(bbox[2])))

    if not paragraph_ranges:
        return [(full_x0, full_x1)]

    paragraph_ranges.sort()
    merged: list[list[float]] = [list(paragraph_ranges[0])]
    for s, e in paragraph_ranges[1:]:
        if s <= merged[-1][1] + _COLUMN_MIN_GUTTER_PX:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(x0, x1) for x0, x1 in merged]


def _figure_bbox(page, page_captions: list[Caption], target: Caption):
    """Compute a bounding rectangle around the figure for ``target``.

    Caption-block-driven, font-aware text-block complement. Handles
    single-column, two-column, page-spanning, and inset/wrapped figures
    uniformly via one signal: the caption paragraph's x-range exactly
    matches the figure's effective width in the layout.

    1. Find the target caption *block* (full paragraph bbox, not just the
       ``Figure N:`` literal). Its x-range becomes the figure column.
    2. Find the nearest other caption — measured by caption-block
       x-overlap, not page-column membership — that bounds the band on
       the side opposite the caption (above for figures, below for tables).
    3. Collect body-paragraph rects inside the band; small spans (figure
       labels) and short blocks (sub-captions, headings) are excluded by
       :func:`_body_text_rects`.
    4. Y-project the body rects to find text-free strips, then select the
       tall-enough strip whose edge touches the caption — or, failing that,
       the tall-enough strip closest to the caption.

    Returns
    -------
    fitz.Rect | None
        The crop rect, or ``None`` if no tall-enough strip is found
        (caller falls back to manual crop or whole-page render).
    """
    import fitz

    target_rect = _find_caption_rect(page, target.kind, target.number)
    if target_rect is None:
        return None

    cap_block = _find_caption_block(page, target.kind, target.number)
    if cap_block is None:
        # Couldn't isolate the full caption paragraph; use the literal rect.
        cap_block = target_rect

    body_size = _body_font_size(page)

    # The figure column matches the caption paragraph's x-range.
    col_x0 = max(page.rect.x0 + _PAGE_MARGIN_PX, cap_block.x0 - _COLUMN_PAD_PX)
    col_x1 = min(page.rect.x1 - _PAGE_MARGIN_PX, cap_block.x1 + _COLUMN_PAD_PX)
    if col_x1 - col_x0 < _MIN_FIG_WIDTH_PX:
        return None

    def _try_direction(look_below: bool):
        """Compute crop band on one side of the caption and select a strip.

        ``look_below=True`` searches below the caption (table-above-caption
        convention or table caption-below table where the table is above);
        ``look_below=False`` searches above (figure convention).
        """
        bound_y_local = None
        for c in page_captions:
            if (c.kind, c.number) == (target.kind, target.number):
                continue
            other_block = _find_caption_block(page, c.kind, c.number)
            if other_block is None:
                other_block = _find_caption_rect(page, c.kind, c.number)
            if other_block is None:
                continue
            x_overlap = max(
                0.0, min(other_block.x1, col_x1) - max(other_block.x0, col_x0)
            )
            if x_overlap < _MIN_FIG_WIDTH_PX:
                continue
            if look_below:
                if other_block.y0 <= cap_block.y1:
                    continue
                bound_y_local = (
                    other_block.y0
                    if bound_y_local is None
                    else min(bound_y_local, other_block.y0)
                )
            else:
                if other_block.y1 >= cap_block.y0:
                    continue
                bound_y_local = (
                    other_block.y1
                    if bound_y_local is None
                    else max(bound_y_local, other_block.y1)
                )

        if look_below:
            floor_y = (
                (bound_y_local - _BBOX_PADDING_PX)
                if bound_y_local is not None
                else (page.rect.y1 - _PAGE_MARGIN_PX)
            )
            band = fitz.Rect(
                col_x0, cap_block.y1 + _BBOX_PADDING_PX, col_x1, floor_y
            )
        else:
            ceiling_y = (
                (bound_y_local + _BBOX_PADDING_PX)
                if bound_y_local is not None
                else (page.rect.y0 + _PAGE_MARGIN_PX)
            )
            band = fitz.Rect(
                col_x0, ceiling_y, col_x1, cap_block.y0 - _BBOX_PADDING_PX
            )

        if band.height < _MIN_BBOX_HEIGHT_PX:
            return None

        text_rects = _body_text_rects(page, band, body_size)
        y_free = _free_intervals(
            [(r.y0, r.y1) for r in text_rects], band.y0, band.y1
        )
        tall = [t for t in y_free if (t[1] - t[0]) >= _MIN_BBOX_HEIGHT_PX]
        if not tall:
            return None

        # Prefer a strip touching the caption edge; else the closest one.
        if look_below:
            touching = [t for t in tall if t[0] <= band.y0 + _GAP_MERGE_PX]
            if touching:
                fy0, fy1 = max(touching, key=lambda t: t[1] - t[0])
            else:
                fy0, fy1 = min(tall, key=lambda t: t[0])
        else:
            touching = [t for t in tall if t[1] >= band.y1 - _GAP_MERGE_PX]
            if touching:
                fy0, fy1 = max(touching, key=lambda t: t[1] - t[0])
            else:
                fy0, fy1 = max(tall, key=lambda t: t[1])

        return fitz.Rect(col_x0, fy0, col_x1, fy1)

    # Figures: caption below figure → look above.
    # Tables: convention varies — IEEE/ACM put caption above the table
    # (look below), but NeurIPS/arXiv often put it below (look above).
    # Try the convention-default first, fall back to the other side.
    if target.kind == "Table":
        return _try_direction(look_below=True) or _try_direction(look_below=False)
    return _try_direction(look_below=False)


def _manual_crops_path(slug: str) -> Path:
    """``papers/<slug>/.cache/figures/manual_crops.json``."""
    return figures_cache_dir(slug) / "manual_crops.json"


def _load_manual_crop(slug: str, kind: str, number: int):
    """Return ``(page, [x0, y0, x1, y1])`` for a manual crop, or ``None``.

    Format of ``manual_crops.json``::

        {
          "figure5": {"page": 3, "bbox": [60.0, 110.0, 300.0, 260.0]},
          "table1":  {"page": 7, "bbox": [50.0, 200.0, 540.0, 380.0]}
        }

    Coordinates are PDF points (the same units PyMuPDF uses). Pages are
    1-based to match :class:`Caption`.
    """
    import json

    path = _manual_crops_path(slug)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = data.get(f"{kind.lower()}{number}")
    if not isinstance(entry, dict):
        return None
    bbox = entry.get("bbox")
    page = entry.get("page")
    if (
        not isinstance(page, int)
        or not isinstance(bbox, list)
        or len(bbox) != 4
        or not all(isinstance(v, (int, float)) for v in bbox)
    ):
        return None
    return page, [float(v) for v in bbox]


def _manual_crop_instructions(slug: str, kind: str, number: int, page: int) -> str:
    key = f"{kind.lower()}{number}"
    path = _manual_crops_path(slug)
    return (
        f"[figures] Auto-crop failed for {kind} {number} on page {page}. "
        f"Falling back to whole-page render. To override, add an entry to "
        f"{path}:\n"
        f'  {{ "{key}": {{ "page": {page}, '
        f'"bbox": [x0, y0, x1, y1] }} }}\n'
        f"(coordinates are PDF points; open the PDF in a viewer that shows "
        f"them, or eyeball from the whole-page render)."
    )


def extract_figure(
    slug: str,
    kind: str,
    number: int,
    pdf_path: Path | None = None,
    *,
    dpi: int = 150,
    refresh: bool = False,
    whole_page: bool = False,
) -> Path:
    """Render the bounding rectangle of a figure or table as a PNG.

    Resolution order:

    1. **Manual crop cache** — ``papers/<slug>/.cache/figures/manual_crops.json``.
       If an entry exists for this figure, its bbox is used verbatim. This is
       the user's escape hatch for figures the heuristic can't isolate.
    2. **2D text-block complement** heuristic. The figure's page is divided
       into a band above the caption; text blocks are subtracted in both x
       and y to find the figure rectangle. Handles row-of-figures pages and
       text-wrap layouts.
    3. **Whole-page render**. Used when both above fail. Stderr gets a
       human-readable instruction for adding a manual override.

    Pass ``whole_page=True`` to skip steps 1 and 2 entirely.

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
    whole_page : bool
        If ``True``, skip the crop heuristic and render the entire page.

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

    import sys

    pdf = (pdf_path or repo_pdf_path(slug)).resolve()
    doc = fitz.open(str(pdf))
    try:
        # Manual crops take priority — they're the user's explicit override.
        manual = None if whole_page else _load_manual_crop(slug, kind_n, number)
        if manual is not None:
            page_num, mbbox = manual
            page = doc[page_num - 1]
            pix = page.get_pixmap(
                dpi=dpi,
                clip=fitz.Rect(mbbox[0], mbbox[1], mbbox[2], mbbox[3]),
            )
        else:
            page = doc[match.page - 1]
            bbox = None
            if not whole_page:
                page_captions = [c for c in captions if c.page == match.page]
                bbox = _figure_bbox(page, page_captions, match)
                if bbox is None:
                    print(
                        _manual_crop_instructions(
                            slug, kind_n, number, match.page
                        ),
                        file=sys.stderr,
                    )
            if bbox is not None:
                pix = page.get_pixmap(dpi=dpi, clip=bbox)
            else:
                pix = page.get_pixmap(dpi=dpi)
        cache.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(cache))
    finally:
        doc.close()
    return cache


def extract_figure_to_vault(
    slug: str,
    kind: str,
    number: int,
    pdf_path: Path | None = None,
    *,
    dpi: int = 150,
    refresh: bool = False,
    whole_page: bool = False,
    relative_dir: str = "figures",
) -> Path:
    """Extract a figure and copy it into the per-paper vault folder.

    Wraps :func:`extract_figure` and copies the resulting PNG to
    ``<vault>/<slug>/<relative_dir>/<kind><N>.png``. Returns the path
    *relative* to ``vault_slug_dir(slug)`` so it can be embedded in
    ``slides.md`` (or any other vault markdown) as a portable link that
    every Marp/Obsidian renderer will resolve, including across drives
    and OneDrive-synced vaults where absolute repo paths fail.

    Parameters
    ----------
    slug : str
        Paper slug.
    kind, number, pdf_path, dpi, refresh, whole_page
        Forwarded to :func:`extract_figure`.
    relative_dir : str
        Subfolder under ``<vault>/<slug>/`` to copy into. Defaults to
        ``"figures"``.

    Returns
    -------
    Path
        Vault-relative path (e.g., ``figures/figure3.png``) suitable for
        embedding in ``![](...)``.
    """
    import shutil

    src = extract_figure(
        slug,
        kind,
        number,
        pdf_path=pdf_path,
        dpi=dpi,
        refresh=refresh,
        whole_page=whole_page,
    )
    dst_dir = vault_slug_dir(slug) / relative_dir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if refresh or not dst.is_file() or dst.stat().st_mtime < src.stat().st_mtime:
        shutil.copy2(src, dst)
    return Path(relative_dir) / src.name


def _cli() -> None:
    """Command-line interface.

    Usage::

        python -m tools.figures list <slug>
        python -m tools.figures extract <slug> <kind> <number> [--dpi N] [--refresh]
        python -m tools.figures extract-to-vault <slug> <kind> <number> [--dpi N] [--refresh]
        python -m tools.figures by-component <slug> <component>
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
    p_ex.add_argument(
        "--whole-page",
        action="store_true",
        help="Skip the crop heuristic; render the entire page.",
    )

    p_ev = sub.add_parser(
        "extract-to-vault",
        help="Extract a figure and copy it into the per-paper vault folder.",
    )
    p_ev.add_argument("slug")
    p_ev.add_argument("kind", choices=["Figure", "Table", "figure", "table"])
    p_ev.add_argument("number", type=int)
    p_ev.add_argument("--dpi", type=int, default=150)
    p_ev.add_argument("--refresh", action="store_true")
    p_ev.add_argument(
        "--whole-page",
        action="store_true",
        help="Skip the crop heuristic; render the entire page.",
    )

    p_by = sub.add_parser(
        "by-component",
        help="Find figures whose prose context mentions a component.",
    )
    p_by.add_argument("slug")
    p_by.add_argument("component")

    args = parser.parse_args()
    if args.cmd == "list":
        for c in list_figures(args.slug):
            print(f"{c.kind} {c.number} (p.{c.page}): {c.caption}")
    elif args.cmd == "by-component":
        for c in captions_by_component(args.slug, args.component):
            print(f"{c.kind} {c.number} (p.{c.page}): {c.caption}")
    elif args.cmd == "extract":
        print(
            extract_figure(
                args.slug,
                args.kind,
                args.number,
                dpi=args.dpi,
                refresh=args.refresh,
                whole_page=args.whole_page,
            )
        )
    elif args.cmd == "extract-to-vault":
        print(
            extract_figure_to_vault(
                args.slug,
                args.kind,
                args.number,
                dpi=args.dpi,
                refresh=args.refresh,
                whole_page=args.whole_page,
            )
        )


if __name__ == "__main__":
    _cli()
