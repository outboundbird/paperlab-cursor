"""PaperLab acquirer -> dissector auto-chain hook.

Runs after any ``Write`` or ``StrReplace`` (``afterFileEdit`` event in
Cursor's hook system). Fires the Acquirer -> Dissector handoff when the
Acquirer finishes a run.

Why ``paper-info.md`` is the trigger
------------------------------------
``paper-info.md`` is the Acquirer's guaranteed final write on every run
(both ``acquire`` and ``rerun``). It is the one event that fires in both
acquisition flows:

1. Agent fetched the PDF -> writes ``paper-info.md`` -> PDF present ->
   chain to Dissector.
2. PDF could not be fetched -> writes ``paper-info.md`` -> PDF missing ->
   do NOT chain; tell the user to download manually and ``rerun``. After
   the manual download, ``/acquirer rerun <slug>`` rewrites
   ``paper-info.md``, re-firing this hook, which now sees the PDF and
   chains.

A manual file drop of ``<slug>.pdf`` fires no agent event, so triggering
on "PDF appeared" would never catch flow 2. Triggering on
``paper-info.md`` + gating on PDF existence covers both.

Gate
----
The hook is a no-op unless the edited file is ``paper-info.md`` under a
per-paper vault folder. When it is, the hook checks whether
``<slug>.pdf`` exists at ``repo_pdf_path(slug)``:

- **PDF present** -> inject ``additional_context`` instructing the agent
  to invoke the Dissector subagent for ``<slug>`` (overwriting an
  existing ``spec.md`` with a warning, per the regenerate-prompt
  exception).
- **PDF missing** -> inject ``additional_context`` instructing the agent
  NOT to dissect and to surface the manual-download prompt.

The hook fails open: any unexpected exception is logged to stderr and
the file write is never blocked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Make sure we can import tools.* regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _emit(payload: dict) -> None:
    """Print the hook output JSON and exit 0."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)


def _present_message(slug: str, pdf_path: Path) -> str:
    return (
        f"Acquirer -> Dissector auto-chain: `paper-info.md` for `{slug}` "
        f"was just written and the PDF is present at {pdf_path}. "
        f"Now invoke the Dissector subagent for `{slug}` automatically "
        f"— do not ask the user for confirmation. If `spec.md` already "
        f"exists, overwrite it and warn the user it was replaced (the "
        f"acquirer/dissector auto-chain exception in "
        f"`paperlab-regenerate-prompt.mdc` applies)."
    )


def _missing_message(slug: str, pdf_path: Path) -> str:
    return (
        f"Acquirer -> Dissector auto-chain: `paper-info.md` for `{slug}` "
        f"was written but no PDF exists at {pdf_path}. Do NOT run the "
        f"Dissector — it would have nothing to read. Surface the "
        f"manual-download prompt: ask the user to place the PDF at the "
        f"path above, then re-run `/acquirer rerun {slug}` to resume the "
        f"chain."
    )


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"dissect_on_acquire: bad stdin ({exc})\n")
        _emit({})

    file_field = (
        payload.get("file_path")
        or payload.get("path")
        or (payload.get("tool_input") or {}).get("path")
        or (payload.get("tool_input") or {}).get("file_path")
    )
    if not file_field:
        _emit({})

    file_path = Path(file_field).resolve()

    # Cheap filename gate before importing anything heavy.
    if file_path.name != "paper-info.md":
        _emit({})

    try:
        from tools.paths import repo_pdf_path, vault_root
    except Exception as exc:
        sys.stderr.write(
            f"dissect_on_acquire: failed to import PaperLab tools "
            f"({exc}); is the hook running from the repo root?\n"
        )
        _emit({})

    try:
        vroot = vault_root()
    except Exception as exc:
        sys.stderr.write(
            f"dissect_on_acquire: cannot resolve vault_root ({exc}); "
            f"skipping.\n"
        )
        _emit({})

    try:
        rel = file_path.relative_to(vroot)
    except ValueError:
        sys.stderr.write("dissect_on_acquire: skip — outside vault\n")
        _emit({})

    if len(rel.parts) < 2:
        sys.stderr.write(
            "dissect_on_acquire: skip — not under a per-paper folder\n"
        )
        _emit({})

    slug = rel.parts[0]

    try:
        pdf_path = repo_pdf_path(slug)
    except Exception as exc:
        sys.stderr.write(
            f"dissect_on_acquire: cannot resolve repo_pdf_path ({exc}); "
            f"skipping.\n"
        )
        _emit({})

    if Path(pdf_path).exists():
        _emit({"additional_context": _present_message(slug, Path(pdf_path))})
    else:
        _emit({"additional_context": _missing_message(slug, Path(pdf_path))})


if __name__ == "__main__":
    main()
