"""PaperLab post-hoc verifier hook.

Runs after any ``Write`` or ``StrReplace`` (``afterFileEdit`` event in
Cursor's hook system). Inspects the edited file; if it is an
agent-generated ``.md`` file inside the PaperLab vault that was NOT
already gated inline (Tutor / Explainer-intermediate), runs the LaTeX
verifier on it and appends findings to the per-paper
``verifier_log.md``.

Skip logic — the hook is a no-op when any of these is true:

- File is not under ``vault_root() / <slug> / ...``.
- File extension is not ``.md``.
- File lacks a YAML front-matter ``agent:`` field (legacy vault content).
- ``agent: tutor`` (already gated inline by R10).
- ``agent: explainer`` AND filename matches ``*-<slug>.md`` (backend
  intermediate that the Tutor will re-verify when composing the
  user-facing file).

For all other agents (``acquirer``, ``dissector``, ``implementer``,
``critic``, future agents) the hook invokes
``tools.verify_latex.verify_text`` directly and reports findings via:

1. An appended block in ``vault_path(slug, "verifier_log.md")``.
2. An ``additional_context`` field in the hook's JSON output so the
   calling agent sees the result in chat.

The hook fails open: any unexpected exception is caught and logged to
stderr; the file write itself is never blocked.
"""

from __future__ import annotations

import datetime as _dt
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


def _parse_front_matter(text: str) -> dict | None:
    """Extract YAML front-matter as a flat ``str -> str`` dict, or
    ``None`` if no front-matter is present.

    Intentionally minimal — only top-level scalar keys are read. Lists
    (e.g. ``tags:``) and nested mappings are ignored. This is enough
    to read the ``agent:`` and ``paper:`` fields the hook needs.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[3:end].strip("\n")
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line or line.lstrip().startswith("-"):
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def _should_skip(file_path: Path, vault_root: Path) -> tuple[bool, str]:
    """Decide whether to skip verification.

    Returns a ``(skip, reason)`` tuple. ``reason`` is empty when not
    skipping.
    """
    if file_path.suffix.lower() != ".md":
        return True, "not a markdown file"
    try:
        rel = file_path.resolve().relative_to(vault_root)
    except ValueError:
        return True, "outside vault"
    parts = rel.parts
    if len(parts) < 2:
        return True, "not under a per-paper folder"
    slug = parts[0]
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return True, f"unreadable: {exc}"
    fm = _parse_front_matter(text)
    if not fm or "agent" not in fm:
        return True, "no agent: front-matter field"
    agent = fm["agent"]
    if agent == "tutor":
        return True, "tutor output is gated inline (R10)"
    if agent == "explainer":
        stem = file_path.stem
        if stem.endswith(f"-{slug}"):
            return True, "explainer intermediate; tutor will re-verify"
    return False, ""


def _format_log_block(
    file_path: Path,
    agent: str,
    findings: list[dict],
    timestamp: str,
) -> str:
    """Render one append-block for ``verifier_log.md``."""
    lines = [
        "",
        f"## {timestamp} — latex-verifier — {file_path.name}",
        f"- agent: {agent}",
    ]
    if not findings:
        lines.append("- clean (no LaTeX issues found)")
        lines.append("")
        return "\n".join(lines)
    for f in findings:
        marker = "ERROR" if f["severity"] == "error" else "WARN "
        loc = (
            f"block #{f['block_index']}"
            if f["block_index"] is not None
            else "whole doc"
        )
        lines.append(
            f"- {marker} {loc}, line {f['line']}: {f['rule_id']} — {f['message']}"
        )
    lines.append("")
    return "\n".join(lines)


def _append_log(log_path: Path, block: str, slug: str) -> None:
    """Append ``block`` to ``log_path``, creating the file with a
    header if it does not exist.
    """
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "---\n"
            f"paper: {slug}\n"
            "category: verifier\n"
            "agent: latex-verifier\n"
            "tags:\n"
            "- AI-guided-paper-reading\n"
            "- verifier-log\n"
            "---\n\n"
            f"# Verifier log — {slug}\n\n"
            "> Append-only log of post-hoc verifier findings on this "
            "paper's vault files.\n"
            "> Generated by `tools/hooks/verify_on_vault_write.py`.\n"
        )
        log_path.write_text(header, encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(block)


def _format_agent_message(
    file_path: Path, findings: list[dict]
) -> str:
    """Render the message returned to the calling agent via
    ``additional_context``.
    """
    errors = [f for f in findings if f["severity"] == "error"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    if not findings:
        return (
            f"LaTeX verifier (post-hoc): {file_path.name} clean "
            f"(no LaTeX issues)."
        )
    lines = [
        f"LaTeX verifier (post-hoc): {file_path.name} — "
        f"{len(errors)} error(s), {len(warnings)} warning(s).",
    ]
    for f in findings:
        loc = (
            f"block #{f['block_index']}"
            if f["block_index"] is not None
            else "whole doc"
        )
        lines.append(
            f"- {f['severity'].upper()} {loc}, line {f['line']}: "
            f"{f['rule_id']} — {f['message']}"
        )
    return "\n".join(lines)


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"verify_on_vault_write: bad stdin ({exc})\n")
        _emit({})

    file_field = (
        payload.get("file_path")
        or payload.get("path")
        or (payload.get("tool_input") or {}).get("path")
        or (payload.get("tool_input") or {}).get("file_path")
    )
    if not file_field:
        _emit({})

    try:
        from tools.paths import vault_path, vault_root
        from tools.verify_latex import verify_text
    except Exception as exc:
        sys.stderr.write(
            f"verify_on_vault_write: failed to import PaperLab tools "
            f"({exc}); is the hook running from the repo root?\n"
        )
        _emit({})

    file_path = Path(file_field).resolve()
    try:
        vroot = vault_root()
    except Exception as exc:
        sys.stderr.write(
            f"verify_on_vault_write: cannot resolve vault_root ({exc}); "
            f"skipping.\n"
        )
        _emit({})

    skip, reason = _should_skip(file_path, vroot)
    if skip:
        sys.stderr.write(f"verify_on_vault_write: skip — {reason}\n")
        _emit({})

    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"verify_on_vault_write: read failed ({exc})\n")
        _emit({})

    fm = _parse_front_matter(text) or {}
    agent = fm.get("agent", "unknown")
    slug = file_path.resolve().relative_to(vroot).parts[0]

    try:
        findings = verify_text(text)
    except Exception as exc:
        sys.stderr.write(
            f"verify_on_vault_write: verifier crashed ({exc}); "
            f"failing open.\n"
        )
        _emit({})

    findings_as_dicts = [f.to_dict() for f in findings]
    timestamp = _dt.datetime.now().strftime("%Y-%m-%dT%H:%M")
    block = _format_log_block(file_path, agent, findings_as_dicts, timestamp)

    try:
        log_path = vault_path(slug, "verifier_log.md")
        _append_log(log_path, block, slug)
    except Exception as exc:
        sys.stderr.write(
            f"verify_on_vault_write: log append failed ({exc}); "
            f"continuing.\n"
        )

    message = _format_agent_message(file_path, findings_as_dicts)
    _emit({"additional_context": message})


if __name__ == "__main__":
    main()
