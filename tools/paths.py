"""Path helpers for PaperLab.

All PaperLab subagents and scripts should construct paths through this module
rather than concatenating strings. Paths are resolved from
``paperlab.config.yaml`` at the repo root.

Two locations:

- **Repo** (this checkout) holds source material (PDFs, supplementals, cloned
  upstream code) and sandbox experiments.
- **Vault** (an Obsidian subtree) holds all agent-generated markdown, slides,
  diagrams, and tldraw canvases — flat under ``<vault>/<slug>/``.

Examples
--------
>>> from tools.paths import vault_path, repo_pdf_path
>>> vault_path("memento", "spec.md")
PosixPath('.../PaperLab/memento/spec.md')
>>> repo_pdf_path("memento")
PosixPath('.../paperlab-cursor/papers/memento/memento.pdf')
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


CONFIG_FILENAME = "paperlab.config.yaml"


def _find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` to find the directory containing
    ``paperlab.config.yaml``.

    Parameters
    ----------
    start : Path, optional
        Directory to start the search from. Defaults to this file's directory.

    Returns
    -------
    Path
        Directory containing ``paperlab.config.yaml``.

    Raises
    ------
    FileNotFoundError
        If no ``paperlab.config.yaml`` is found in any parent directory.
    """
    here = (start or Path(__file__).resolve().parent).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / CONFIG_FILENAME).is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not find {CONFIG_FILENAME} in any parent of {here}. "
        f"Copy paperlab.config.example.yaml to paperlab.config.yaml and edit "
        f"the paths for this machine."
    )


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Load and cache ``paperlab.config.yaml``.

    Returns
    -------
    dict
        The parsed YAML, with at least ``repo_root`` and
        ``vault_paperlab_path`` keys.
    """
    repo = _find_repo_root()
    with (repo / CONFIG_FILENAME).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    for required in ("repo_root", "vault_paperlab_path"):
        if required not in cfg:
            raise KeyError(
                f"{CONFIG_FILENAME} is missing required key: {required!r}"
            )
    return cfg


def repo_root() -> Path:
    """Absolute path to the paperlab-cursor repo root on this machine."""
    return Path(load_config()["repo_root"]).resolve()


def vault_root() -> Path:
    """Absolute path to the PaperLab subtree inside the Obsidian vault.

    Each paper lives at ``vault_root() / slug``.
    """
    return Path(load_config()["vault_paperlab_path"]).resolve()


def obsidian_vault_root() -> Path | None:
    """Absolute path to the curated Obsidian vault root, if configured.

    Used by the ``prerequisite`` and ``explainer`` agents to check whether the
    user has prior notes on a concept. Returns ``None`` if not configured.
    """
    val = load_config().get("obsidian_vault_root")
    return Path(val).resolve() if val else None


# ---------------------------------------------------------------------------
# Vault paths (agent-generated markdown lives here).
# ---------------------------------------------------------------------------


def vault_slug_dir(slug: str) -> Path:
    """``<vault>/<slug>/`` — the per-paper folder for generated notes."""
    return vault_root() / slug


def vault_path(slug: str, filename: str) -> Path:
    """``<vault>/<slug>/<filename>`` — any file inside the per-paper folder."""
    return vault_slug_dir(slug) / filename


# ---------------------------------------------------------------------------
# Repo paths (source material and experiments live here).
# ---------------------------------------------------------------------------


def repo_paper_dir(slug: str) -> Path:
    """``<repo>/papers/<slug>/`` — per-paper source-material folder."""
    return repo_root() / "papers" / slug


def repo_pdf_path(slug: str) -> Path:
    """``<repo>/papers/<slug>/<slug>.pdf`` — the paper PDF."""
    return repo_paper_dir(slug) / f"{slug}.pdf"


def repo_supplementals_dir(slug: str) -> Path:
    """``<repo>/papers/<slug>/supplementals/`` — appendices, supplementary PDFs."""
    return repo_paper_dir(slug) / "supplementals"


def repo_upstream_dir(slug: str) -> Path:
    """``<repo>/papers/<slug>/upstream/<slug>/`` — cloned official git repo."""
    return repo_paper_dir(slug) / "upstream" / slug


def repo_sandbox_dir(slug: str) -> Path:
    """``<repo>/sandbox/<slug>/`` — toy-experiment folder for this paper."""
    return repo_root() / "sandbox" / slug


# ---------------------------------------------------------------------------
# CLI for quick lookups from a shell, useful for agents that prefer subprocess
# calls over Python imports.
# ---------------------------------------------------------------------------


def _cli() -> None:
    """Command-line interface: ``python -m tools.paths <kind> <slug> [name]``.

    Supported ``<kind>`` values:

    - ``vault``  : prints ``vault_path(slug, name)``
    - ``vault-dir`` : prints ``vault_slug_dir(slug)``
    - ``pdf``    : prints ``repo_pdf_path(slug)``
    - ``paper-dir`` : prints ``repo_paper_dir(slug)``
    - ``supplementals`` : prints ``repo_supplementals_dir(slug)``
    - ``upstream`` : prints ``repo_upstream_dir(slug)``
    - ``sandbox`` : prints ``repo_sandbox_dir(slug)``
    """
    import sys

    # The configured vault path may contain non-ASCII characters (e.g. emoji
    # folder names common in Obsidian). On Windows the default console
    # encoding (cp1252) can't represent these, so force UTF-8 on stdout.
    #
    # NOTE: UTF-8 stdout makes resolution work, but downstream shell calls
    # (test -f, ls) against paths containing non-BMP characters (e.g. 🎓)
    # still fail on Windows due to cmd.exe and Cursor's tool-call layer
    # mishandling them. Users should keep `vault_paperlab_path` ASCII up to
    # the `PaperLab/` segment. See AGENTS.md "Windows path warning" and
    # ROADMAP.md "Known limitations".
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(_cli.__doc__)
        return

    kind = args[0]
    slug = args[1] if len(args) > 1 else None
    name = args[2] if len(args) > 2 else None

    if kind == "vault":
        if not (slug and name):
            raise SystemExit("usage: python -m tools.paths vault <slug> <filename>")
        print(vault_path(slug, name))
    elif kind == "vault-dir":
        print(vault_slug_dir(slug))
    elif kind == "pdf":
        print(repo_pdf_path(slug))
    elif kind == "paper-dir":
        print(repo_paper_dir(slug))
    elif kind == "supplementals":
        print(repo_supplementals_dir(slug))
    elif kind == "upstream":
        print(repo_upstream_dir(slug))
    elif kind == "sandbox":
        print(repo_sandbox_dir(slug))
    else:
        raise SystemExit(f"Unknown kind: {kind!r}. Run with --help.")


if __name__ == "__main__":
    _cli()
