"""PDF text extraction helpers for PaperLab.

All PaperLab subagents that need to read a paper PDF (dissector, implementer,
critic, explainer, ...) should call :func:`extract_pdf_text` rather than
shelling out to ad-hoc tools. This guarantees a single canonical extraction
path and a cached result so every agent sees the same text.

Extraction strategy
-------------------
1. ``pypdf`` (pinned in ``requirements.txt``). Pure-Python, works everywhere.
2. ``pdftotext`` (Poppler) if available on PATH — used only as a fallback
   when ``pypdf`` raises.

Results are cached to ``<repo>/papers/<slug>/.cache/<source>.txt`` (the
``papers/`` tree is git-ignored). Pass ``refresh=True`` to force re-extraction.

Examples
--------
>>> from tools.pdf import extract_pdf_text
>>> text = extract_pdf_text("WorldModel")
>>> "world model" in text.lower()
True
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tools.paths import repo_paper_dir, repo_pdf_path


def extracted_cache_path(slug: str, source: str = "paper") -> Path:
    """Return the cache path for extracted PDF text.

    Parameters
    ----------
    slug : str
        Paper slug (unmodified, as the user provided it).
    source : str
        Logical name of the PDF — ``"paper"`` for the main PDF, or a
        supplement stem for supplementals.
    """
    return repo_paper_dir(slug) / ".cache" / f"{source}.txt"


def _extract_with_pypdf(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_with_pdftotext(pdf_path: Path) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext not found on PATH")
    result = subprocess.run(
        [exe, "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def extract_pdf_text(
    slug: str,
    pdf_path: Path | None = None,
    *,
    source: str = "paper",
    refresh: bool = False,
) -> str:
    """Extract and cache text from a paper PDF.

    Parameters
    ----------
    slug : str
        Paper slug. Used to resolve the default PDF location and cache path.
    pdf_path : Path, optional
        Explicit PDF path. Defaults to :func:`repo_pdf_path(slug)
        <tools.paths.repo_pdf_path>`. Pass an explicit path when extracting
        a supplement; also set ``source`` to a unique name.
    source : str
        Logical PDF name for the cache file. Default ``"paper"``.
    refresh : bool
        If ``True``, ignore any cached extraction and re-run.

    Returns
    -------
    str
        Full extracted text.

    Raises
    ------
    FileNotFoundError
        If the PDF does not exist.
    RuntimeError
        If both ``pypdf`` and ``pdftotext`` are unavailable or fail.
    """
    pdf = (pdf_path or repo_pdf_path(slug)).resolve()
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    cache = extracted_cache_path(slug, source)
    if cache.is_file() and not refresh:
        return cache.read_text(encoding="utf-8")

    errors: list[str] = []
    text: str | None = None
    for name, fn in (("pypdf", _extract_with_pypdf), ("pdftotext", _extract_with_pdftotext)):
        try:
            text = fn(pdf)
            break
        except Exception as exc:  # noqa: BLE001 — surface both errors together
            errors.append(f"{name}: {exc}")

    if text is None:
        raise RuntimeError(
            "Failed to extract PDF text. Tried:\n  - " + "\n  - ".join(errors)
        )

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def _cli() -> None:
    """Command-line interface.

    Usage:
        python -m tools.pdf extract <slug> [--source NAME] [--refresh]
        python -m tools.pdf cache-path <slug> [--source NAME]
    """
    import argparse
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(prog="python -m tools.pdf")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract (and cache) PDF text; print to stdout.")
    p_extract.add_argument("slug")
    p_extract.add_argument("--source", default="paper")
    p_extract.add_argument("--refresh", action="store_true")

    p_cache = sub.add_parser("cache-path", help="Print the cache path for a slug.")
    p_cache.add_argument("slug")
    p_cache.add_argument("--source", default="paper")

    args = parser.parse_args()

    if args.cmd == "extract":
        print(extract_pdf_text(args.slug, source=args.source, refresh=args.refresh))
    elif args.cmd == "cache-path":
        print(extracted_cache_path(args.slug, args.source))


if __name__ == "__main__":
    _cli()
