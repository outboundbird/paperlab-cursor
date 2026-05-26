"""Build the visualizer dictionary PDF (reference card).

Parses ``.cursor/skills/ml-visualization/DICTIONARY.md`` and emits a PDF
that mirrors its three tables (Entities, Relations, Actions) with an
extra **Symbol** column holding the per-entry PNG tile rendered by
``tools.build_symbol_sheet``.

Run:

    python -m tools.build_dictionary_pdf

This implicitly invokes ``tools.build_symbol_sheet.main()`` first to
ensure tiles are fresh, then writes:

    .cursor/skills/ml-visualization/DICTIONARY.pdf

Sync semantics
--------------

The list of rows in the PDF is parsed directly from ``DICTIONARY.md``,
so adding/removing/renaming an entry there propagates automatically.
The symbol cell is populated only for entries that have a registered
renderer in ``build_symbol_sheet.RENDERERS``; entries without one get
a placeholder ``— no tile —`` cell, making sync drift visible inside
the PDF itself.

Implementation notes
--------------------

- Pure ReportLab — no LaTeX, no pandoc, no extra binaries beyond what
  ``build_symbol_sheet`` already needs (graphviz ``dot``).
- Math inside ``$...$`` is rendered as literal text (the ``$`` markers
  are stripped). ReportLab's mathtext support is too limited to be
  worth the complexity here, and the dictionary already uses Unicode
  for most math glyphs.
- Inline backtick-code is rendered as a monospaced span.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from tools import build_symbol_sheet
from tools.paths import repo_root


SKILL_DIR = repo_root() / ".cursor" / "skills" / "ml-visualization"
DICT_PATH = SKILL_DIR / "DICTIONARY.md"
SYMBOLS_DIR = SKILL_DIR / "symbols"
AUTO_DIR = SYMBOLS_DIR / "auto"
PDF_PATH = SKILL_DIR / "DICTIONARY.pdf"


# ---------------------------------------------------------------------------
# Dictionary parsing.
# ---------------------------------------------------------------------------


SECTION_HEADER_RE = re.compile(r"^##\s+(Entities|Relations|Actions)\b", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"^\|\s*([EAR]\d+)\s*\|(.+)\|\s*$")

# Inline markdown image reference, e.g. ``![alt](symbols/E1.png)``. The dictionary
# uses this to attach a user-drawn picture to a row; the build script extracts the
# path, strips the ``![](...)`` text from the prose, and inserts the picture into
# the PDF's Symbol column. Captures the alt text and the relative path.
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _extract_user_png(symbolic_cell: str) -> tuple[str, Path | None]:
    """Pull the first ``![](path)`` image reference out of a symbolic-rep cell.

    Returns
    -------
    cleaned_cell : str
        The cell text with the matched image reference removed so the
        markdown image syntax doesn't appear as literal text alongside the
        rendered picture in the PDF.
    png_path : Path or None
        Resolved absolute path to the PNG (relative paths resolve against
        ``DICT_PATH.parent``), or ``None`` if no image reference was present
        or the referenced file does not exist on disk.
    """
    m = MD_IMAGE_RE.search(symbolic_cell)
    if not m:
        return symbolic_cell, None

    rel = m.group(2).strip()
    candidate = (DICT_PATH.parent / rel).resolve()
    png = candidate if candidate.is_file() else None

    # Strip the markdown image-ref token and any leftover whitespace/punctuation
    # immediately around it (a hanging "; " or "  " left behind by the removal).
    cleaned = MD_IMAGE_RE.sub("", symbolic_cell)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"[;,\s]+$", "", cleaned)
    return cleaned, png


def _parse_sections(text: str) -> dict[str, list[tuple[str, str, str, str, Path | None]]]:
    """Extract the three category tables from ``DICTIONARY.md``.

    Returns
    -------
    dict
        Maps category name (``"Entities"`` / ``"Relations"`` / ``"Actions"``)
        to a list of ``(id, canonical_name, aliases, symbolic_representation,
        user_png_path)`` tuples in source order. ``user_png_path`` is the
        resolved absolute path to a user-drawn PNG embedded in the cell via
        ``![](symbols/<id>.png)``, or ``None`` if no such reference is present.
        When ``user_png_path`` is not None, the matching ``![](...)`` token has
        already been stripped from ``symbolic_representation``.
    """
    sections: dict[str, list[tuple[str, str, str, str, Path | None]]] = {}

    headers = [(m.group(1), m.start()) for m in SECTION_HEADER_RE.finditer(text)]
    for i, (name, start) in enumerate(headers):
        end = headers[i + 1][1] if i + 1 < len(headers) else len(text)
        body = text[start:end]
        rows: list[tuple[str, str, str, str, Path | None]] = []
        for line in body.splitlines():
            m = TABLE_ROW_RE.match(line)
            if not m:
                continue
            entry_id = m.group(1).strip()
            cells = [c.strip() for c in m.group(2).split("|")]
            if len(cells) < 3:
                continue
            canonical, aliases, symbolic = cells[0], cells[1], cells[2]
            symbolic, user_png = _extract_user_png(symbolic)
            rows.append((entry_id, canonical, aliases, symbolic, user_png))
        sections[name] = rows

    return sections


# ---------------------------------------------------------------------------
# Markdown-cell to ReportLab-paragraph rendering.
# ---------------------------------------------------------------------------


# Minimal LaTeX-to-Unicode map for the math fragments that appear inside
# ``$...$`` in DICTIONARY.md. Extend as new commands appear.
_LATEX_TO_UNICODE = {
    r"\sim": "~",
    r"\to": "\u2192",
    r"\leq": "\u2264",
    r"\geq": "\u2265",
    r"\neq": "\u2260",
    r"\approx": "\u2248",
    r"\in": "\u2208",
    r"\subset": "\u2282",
    r"\cup": "\u222a",
    r"\cap": "\u2229",
    r"\sum": "\u03a3",
    r"\prod": "\u03a0",
    r"\int": "\u222b",
    r"\partial": "\u2202",
    r"\nabla": "\u2207",
    r"\infty": "\u221e",
    r"\cdot": "\u00b7",
    r"\circ": "\u2218",
    r"\oplus": "\u2295",
    r"\ldots": "\u2026",
    r"\mid": "|",
    r"\hat": "",
    r"\tilde": "",
    r"\bar": "",
    r"\mathbb{E}": "\U0001d53c",
    r"\mathcal{D}": "\U0001d49f",
    r"\mathcal{X}": "\U0001d4b3",
    r"\mathcal{T}": "\U0001d4af",
    r"\mathcal{N}": "\U0001d4a9",
    r"\mathrm": "",
    r"\mathit": "",
    r"\theta": "\u03b8",
    r"\phi": "\u03c6",
    r"\psi": "\u03c8",
    r"\rho": "\u03c1",
    r"\mu": "\u03bc",
    r"\sigma": "\u03c3",
    r"\epsilon": "\u03b5",
    r"\delta": "\u03b4",
    r"\beta": "\u03b2",
    r"\alpha": "\u03b1",
    r"\gamma": "\u03b3",
    r"\tau": "\u03c4",
    r"\pi": "\u03c0",
    r"\eta": "\u03b7",
    r"\Sigma": "\u03a3",
    r"\Phi": "\u03a6",
    r"\tanh": "tanh",
    r"\max": "max",
    r"\min": "min",
    r"\log": "log",
    r"\exp": "exp",
    r"\left": "",
    r"\right": "",
}


def _expand_latex(s: str) -> str:
    """Replace a handful of LaTeX commands with their Unicode equivalents."""
    # Longest-first so e.g. `\mathbb{E}` matches before `\mathbb` (n/a here,
    # but the principle).
    for cmd in sorted(_LATEX_TO_UNICODE, key=len, reverse=True):
        s = s.replace(cmd, _LATEX_TO_UNICODE[cmd])
    # Strip stray braces left over from `{...}` grouping.
    s = re.sub(r"[{}]", "", s)
    return s


def _md_cell_to_html(text: str) -> str:
    """Convert a dictionary-cell markdown fragment to ReportLab mini-HTML.

    Handles the small subset that appears in ``DICTIONARY.md``:

    - ``$...$`` inline math → plain text (``$`` stripped)
    - ``` `code` ``` → ``<font face="Courier">code</font>``
    - ``**bold**`` → ``<b>bold</b>``
    - ``*italic*`` / ``_italic_`` → ``<i>italic</i>``

    Everything else is HTML-escaped to keep ReportLab happy.
    """
    # 1. Pull out code spans first so their content isn't processed further.
    placeholders: list[str] = []

    def _stash_code(m: re.Match[str]) -> str:
        placeholders.append(html.escape(m.group(1)))
        return f"\x00CODE{len(placeholders) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash_code, text)

    # 2. Strip $...$ math fences (expand the small LaTeX subset to Unicode).
    text = re.sub(r"\$([^$]+)\$", lambda m: _expand_latex(m.group(1)), text)

    # 3. HTML-escape what's left.
    text = html.escape(text)

    # 4. Apply bold / italic.
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)", r"<i>\1</i>", text)

    # 5. Restore code spans.
    def _unstash(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return f'<font face="Courier">{placeholders[idx]}</font>'

    text = re.sub(r"\x00CODE(\d+)\x00", _unstash, text)

    return text


# ---------------------------------------------------------------------------
# PDF assembly.
# ---------------------------------------------------------------------------


# Page geometry: landscape A4 to give the wide "symbolic representation"
# column enough room while keeping symbol tiles legible.
PAGE_SIZE = landscape(A4)
LEFT_MARGIN = RIGHT_MARGIN = TOP_MARGIN = BOTTOM_MARGIN = 12 * mm

# Column widths (sum should be page width - left - right ~= 273 mm on A4
# landscape).
COL_WIDTHS_MM = {
    "id": 14,
    "canonical": 38,
    "aliases": 68,
    "symbolic": 95,
    "symbol": 58,
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["BodyText"]
    cell = ParagraphStyle(
        "cell",
        parent=base,
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        spaceBefore=0,
        spaceAfter=0,
    )
    head = ParagraphStyle(
        "head",
        parent=cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    section = ParagraphStyle(
        "section",
        parent=base,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#0d3b66"),
    )
    title = ParagraphStyle(
        "title",
        parent=section,
        fontSize=18,
        spaceBefore=0,
    )
    intro = ParagraphStyle(
        "intro",
        parent=cell,
        fontSize=9,
        leading=11,
        spaceAfter=6,
    )
    return {
        "cell": cell,
        "head": head,
        "section": section,
        "title": title,
        "intro": intro,
    }


def _symbol_cell(
    entry_id: str,
    user_png: Path | None,
    styles: dict[str, ParagraphStyle],
):
    """Return an ``Image`` flowable for the Symbol column.

    Priority:

    1. ``user_png`` — a PNG referenced from the row's symbolic-rep cell via
       ``![](...)``. The user drew this; respect it.
    2. ``symbols/<id>.png`` — the graphviz auto-rendered tile for entries
       with a registered renderer in ``build_symbol_sheet.RENDERERS``.
    3. ``— no tile —`` placeholder when neither is available.
    """
    png: Path | None = None
    if user_png is not None and user_png.is_file():
        png = user_png
    else:
        auto = AUTO_DIR / f"{entry_id}.png"
        if entry_id in build_symbol_sheet.RENDERERS and auto.exists():
            png = auto

    if png is None:
        return Paragraph(
            '<font color="#888"><i>\u2014 no tile \u2014</i></font>', styles["cell"]
        )

    img = Image(str(png))
    max_w = COL_WIDTHS_MM["symbol"] * mm - 4 * mm
    max_h = 22 * mm
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight, 1.0)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    return img


def _build_table(
    rows: list[tuple[str, str, str, str, Path | None]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    header = [
        Paragraph("#", styles["head"]),
        Paragraph("Canonical name", styles["head"]),
        Paragraph("Aliases", styles["head"]),
        Paragraph("Symbolic representation", styles["head"]),
        Paragraph("Symbol", styles["head"]),
    ]
    data = [header]
    for entry_id, canonical, aliases, symbolic, user_png in rows:
        data.append([
            Paragraph(f"<b>{entry_id}</b>", styles["cell"]),
            Paragraph(_md_cell_to_html(canonical), styles["cell"]),
            Paragraph(_md_cell_to_html(aliases), styles["cell"]),
            Paragraph(_md_cell_to_html(symbolic), styles["cell"]),
            _symbol_cell(entry_id, user_png, styles),
        ])

    col_widths = [
        COL_WIDTHS_MM["id"] * mm,
        COL_WIDTHS_MM["canonical"] * mm,
        COL_WIDTHS_MM["aliases"] * mm,
        COL_WIDTHS_MM["symbolic"] * mm,
        COL_WIDTHS_MM["symbol"] * mm,
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8dc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#90a4ae")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f8fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _build_pdf(sections: dict[str, list[tuple[str, str, str, str, Path | None]]]) -> None:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=PAGE_SIZE,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="PaperLab visualizer dictionary",
        author="PaperLab",
    )

    story: list = []
    story.append(Paragraph("PaperLab visualizer dictionary", styles["title"]))
    story.append(Paragraph(
        "Auto-generated from "
        '<font face="Courier">.cursor/skills/ml-visualization/DICTIONARY.md</font>. '
        "Do not edit this PDF by hand \u2014 edit the markdown source and "
        'rerun <font face="Courier">python -m tools.build_dictionary_pdf</font>. '
        "To attach a hand-drawn symbol to a row, save a PNG under "
        '<font face="Courier">.cursor/skills/ml-visualization/symbols/</font> '
        "and add an inline <font face=\"Courier\">![](symbols/&lt;id&gt;.png)</font> "
        "to that row's Symbolic-representation cell.",
        styles["intro"],
    ))

    total = sum(len(v) for v in sections.values())
    user = sum(
        1 for rows in sections.values() for r in rows
        if r[4] is not None
    )
    auto = sum(
        1 for rows in sections.values() for r in rows
        if r[4] is None and r[0] in build_symbol_sheet.RENDERERS
        and (AUTO_DIR / f"{r[0]}.png").exists()
    )
    placeholder = total - user - auto
    story.append(Paragraph(
        f"<b>{total}</b> entries total \u00b7 "
        f"<b>{user}</b> with user-drawn symbol \u00b7 "
        f"<b>{auto}</b> with graphviz auto-render \u00b7 "
        f"<b>{placeholder}</b> placeholder.",
        styles["intro"],
    ))
    story.append(Spacer(1, 4 * mm))

    for name in ("Entities", "Relations", "Actions"):
        rows = sections.get(name, [])
        if not rows:
            continue
        story.append(Paragraph(f"{name} ({len(rows)})", styles["section"]))
        story.append(_build_table(rows, styles))
        if name != "Actions":
            story.append(PageBreak())

    doc.build(story)


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------


def main(skip_tiles: bool = False) -> None:
    if not DICT_PATH.is_file():
        raise FileNotFoundError(f"DICTIONARY.md not found at {DICT_PATH}")

    if not skip_tiles:
        # Refresh tiles first so the PDF embeds up-to-date PNGs.
        build_symbol_sheet.main()

    sections = _parse_sections(DICT_PATH.read_text(encoding="utf-8"))
    if not sections:
        raise RuntimeError(
            "Failed to parse any sections from DICTIONARY.md \u2014 expected "
            "'## Entities', '## Relations', '## Actions' headers."
        )

    _build_pdf(sections)
    print(f"wrote {PDF_PATH}")


if __name__ == "__main__":
    import sys

    main(skip_tiles="--skip-tiles" in sys.argv)
