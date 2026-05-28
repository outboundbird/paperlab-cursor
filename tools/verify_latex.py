"""LaTeX lexer-only verifier for PaperLab markdown files.

Checks LaTeX correctness in ``$...$`` and ``$$...$$`` blocks of a markdown
document without invoking a real LaTeX engine. Catches the common structural
errors that the Tutor and Explainer subagents have produced in practice:
unmatched braces, unpaired ``\\left``/``\\right``, mismatched
``\\begin``/``\\end`` environments, unbalanced ``$`` delimiters, Unicode
math characters inside math blocks (forbidden per ``AGENTS.md``), and the
``\\(...\\)`` / ``\\[...\\]`` math delimiters that don't render in GitHub
markdown preview.

This is the **v1 lexer** — pure Python, zero dependencies, works on
Windows today. A future **v2 KaTeX** verifier will run the actual
KaTeX strict-mode renderer on each block for stronger guarantees;
it requires Node and is intended for the Linux machine.

Examples
--------
Command-line use::

    python -m tools.verify_latex path/to/file.md
    python -m tools.verify_latex --json path/to/file.md
    cat file.md | python -m tools.verify_latex -

Programmatic use::

    from tools.verify_latex import verify_text
    findings = verify_text(open("file.md", encoding="utf-8").read())
    if any(f.severity == "error" for f in findings):
        ...
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from typing import Iterator, Literal


Severity = Literal["error", "warning"]


@dataclasses.dataclass
class Finding:
    """A single verifier finding.

    Attributes
    ----------
    severity : {"error", "warning"}
        ``error`` blocks emission in the inline gate; ``warning`` does not.
    rule_id : str
        Stable identifier of the rule that fired (e.g. ``brace-balance``).
    line : int
        1-indexed line number in the source document.
    col : int
        1-indexed column number, best effort.
    block_index : int | None
        1-indexed position of the math block in the document when the
        finding is scoped to a math block, else ``None``.
    message : str
        Human-readable description of the issue.
    """

    severity: Severity
    rule_id: str
    line: int
    col: int
    block_index: int | None
    message: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# Unicode math characters forbidden inside $...$ / $$...$$ per AGENTS.md.
# Atomic symbols only; this is not exhaustive but covers the symbols the
# Tutor/Explainer have leaked in observed regressions.
UNICODE_MATH_CHARS = set(
    "θμπσρλΘΛΣΩΠΦΨφψχξζηβγδεκντω"
    "ℝℕℤℚℂℙ𝔼"
    "∑∏∫∮∂∇∞≤≥≠≈≡∈∉⊂⊆⊃⊇∪∩"
    "→←↔⇒⇐⇔↦"
    "·×÷±∓"
    "₀₁₂₃₄₅₆₇₈₉"
    "⁰¹²³⁴⁵⁶⁷⁸⁹"
)

# Environments where bare \\ and & are legitimate (row separators / column
# alignment). Outside these, those tokens are usually mistakes.
TABULAR_ENVS = {
    "array",
    "align",
    "align*",
    "aligned",
    "alignedat",
    "alignat",
    "alignat*",
    "matrix",
    "pmatrix",
    "bmatrix",
    "Bmatrix",
    "vmatrix",
    "Vmatrix",
    "smallmatrix",
    "cases",
    "split",
    "gather",
    "gather*",
    "gathered",
    "eqnarray",
    "eqnarray*",
    "multline",
    "multline*",
    "tabular",
    "tabularx",
    "tabular*",
}


def _strip_fenced_blocks(text: str) -> str:
    """Replace contents of ``mermaid`` and ``tikz`` fenced blocks with
    blank lines of the same count, so line numbers in the rest of the
    document remain accurate while their contents are excluded from
    LaTeX checks.

    Parameters
    ----------
    text : str
        Full markdown source.

    Returns
    -------
    str
        Source with the interior of ```` ```mermaid ```` and
        ```` ```tikz ```` fences blanked.
    """
    pattern = re.compile(
        r"(^```(?:mermaid|tikz)[^\n]*\n)(.*?)(^```\s*$)",
        re.MULTILINE | re.DOTALL,
    )

    def blank_interior(match: re.Match) -> str:
        opening, interior, closing = match.group(1), match.group(2), match.group(3)
        return opening + "\n" * interior.count("\n") + closing

    return pattern.sub(blank_interior, text)


def _strip_code_fences(text: str) -> str:
    """Blank out the interior of any ```` ``` ```` fenced code block so its
    contents are not treated as LaTeX. Preserves line counts.

    Mermaid and tikz fences should already have been blanked by
    :func:`_strip_fenced_blocks` before this is called.
    """
    pattern = re.compile(r"(^```[^\n]*\n)(.*?)(^```\s*$)", re.MULTILINE | re.DOTALL)

    def blank_interior(match: re.Match) -> str:
        opening, interior, closing = match.group(1), match.group(2), match.group(3)
        return opening + "\n" * interior.count("\n") + closing

    return pattern.sub(blank_interior, text)


@dataclasses.dataclass
class MathBlock:
    """A located math block extracted from the document.

    The ``content`` field excludes the delimiters themselves.
    """

    index: int
    kind: Literal["inline", "display"]
    start_line: int
    start_col: int
    content: str


def _iter_math_blocks(text: str) -> Iterator[MathBlock]:
    """Yield math blocks (``$...$`` and ``$$...$$``) with locations.

    A backslash-escaped ``\\$`` does not open or close a block. ``$$`` is
    matched greedily before single ``$``. Mismatched delimiters are not
    reported here; the dollar-balance rule in :func:`verify_text` handles
    them separately.
    """
    i = 0
    n = len(text)
    line = 1
    col = 1
    block_index = 0
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            col = 1
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            i += 2
            col += 2
            continue
        if ch == "$":
            is_display = i + 1 < n and text[i + 1] == "$"
            delim = "$$" if is_display else "$"
            kind: Literal["inline", "display"] = "display" if is_display else "inline"
            start_line, start_col = line, col
            j = i + len(delim)
            jline, jcol = line, col + len(delim)
            content_start = j
            closed = False
            while j < n:
                cj = text[j]
                if cj == "\n":
                    jline += 1
                    jcol = 1
                    j += 1
                    continue
                if cj == "\\" and j + 1 < n:
                    j += 2
                    jcol += 2
                    continue
                if cj == "$":
                    if is_display:
                        if j + 1 < n and text[j + 1] == "$":
                            block_index += 1
                            yield MathBlock(
                                index=block_index,
                                kind=kind,
                                start_line=start_line,
                                start_col=start_col,
                                content=text[content_start:j],
                            )
                            j += 2
                            jcol += 2
                            closed = True
                            break
                        j += 1
                        jcol += 1
                        continue
                    block_index += 1
                    yield MathBlock(
                        index=block_index,
                        kind=kind,
                        start_line=start_line,
                        start_col=start_col,
                        content=text[content_start:j],
                    )
                    j += 1
                    jcol += 1
                    closed = True
                    break
                j += 1
                jcol += 1
            if not closed:
                # Unterminated block; let dollar-balance rule fire later.
                return
            line, col = jline, jcol
            i = j
            continue
        i += 1
        col += 1


def _check_braces(block: MathBlock) -> Iterator[Finding]:
    """Flag unbalanced ``{`` and ``}`` inside a math block."""
    depth = 0
    src = block.content
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                yield Finding(
                    severity="error",
                    rule_id="brace-balance",
                    line=block.start_line,
                    col=block.start_col,
                    block_index=block.index,
                    message=f"unmatched '}}' in math block #{block.index}",
                )
                depth = 0
        i += 1
    if depth > 0:
        yield Finding(
            severity="error",
            rule_id="brace-balance",
            line=block.start_line,
            col=block.start_col,
            block_index=block.index,
            message=(
                f"{depth} unclosed '{{' in math block #{block.index}"
            ),
        )


def _check_left_right(block: MathBlock) -> Iterator[Finding]:
    """Flag unpaired ``\\left`` / ``\\right`` inside a math block."""
    lefts = len(re.findall(r"\\left\b", block.content))
    rights = len(re.findall(r"\\right\b", block.content))
    if lefts != rights:
        yield Finding(
            severity="error",
            rule_id="left-right",
            line=block.start_line,
            col=block.start_col,
            block_index=block.index,
            message=(
                f"\\left/\\right mismatch in math block #{block.index} "
                f"({lefts} \\left vs {rights} \\right)"
            ),
        )


def _check_begin_end(block: MathBlock) -> Iterator[Finding]:
    """Flag ``\\begin{X}`` / ``\\end{X}`` mismatches inside a math block."""
    tokens = re.findall(r"\\(begin|end)\{([^}]+)\}", block.content)
    stack: list[str] = []
    for kind, name in tokens:
        if kind == "begin":
            stack.append(name)
        else:
            if not stack:
                yield Finding(
                    severity="error",
                    rule_id="begin-end",
                    line=block.start_line,
                    col=block.start_col,
                    block_index=block.index,
                    message=(
                        f"\\end{{{name}}} without matching \\begin in math "
                        f"block #{block.index}"
                    ),
                )
                continue
            top = stack.pop()
            if top != name:
                yield Finding(
                    severity="error",
                    rule_id="begin-end",
                    line=block.start_line,
                    col=block.start_col,
                    block_index=block.index,
                    message=(
                        f"\\end{{{name}}} does not match \\begin{{{top}}} "
                        f"in math block #{block.index}"
                    ),
                )
    for name in stack:
        yield Finding(
            severity="error",
            rule_id="begin-end",
            line=block.start_line,
            col=block.start_col,
            block_index=block.index,
            message=(
                f"\\begin{{{name}}} without matching \\end in math "
                f"block #{block.index}"
            ),
        )


def _check_unicode_math(block: MathBlock) -> Iterator[Finding]:
    """Flag Unicode math characters inside a math block (forbidden per
    ``AGENTS.md``).
    """
    for ch in block.content:
        if ch in UNICODE_MATH_CHARS:
            yield Finding(
                severity="error",
                rule_id="unicode-math",
                line=block.start_line,
                col=block.start_col,
                block_index=block.index,
                message=(
                    f"Unicode math character {ch!r} in math block "
                    f"#{block.index}; use LaTeX command instead"
                ),
            )
            return


def _check_stray_tabular_tokens(block: MathBlock) -> Iterator[Finding]:
    """Flag ``\\\\`` and bare ``&`` outside known tabular/aligned envs.

    ``\\\\`` and ``&`` are only meaningful inside environments like
    ``array``, ``align``, ``matrix``, ``cases``, etc. Outside those, they
    are nearly always mistakes.
    """
    begin_envs = {m.group(1) for m in re.finditer(r"\\begin\{([^}]+)\}", block.content)}
    if begin_envs & TABULAR_ENVS:
        return
    if re.search(r"(?<!\\)\\\\", block.content):
        yield Finding(
            severity="warning",
            rule_id="stray-newline",
            line=block.start_line,
            col=block.start_col,
            block_index=block.index,
            message=(
                f"'\\\\' in math block #{block.index} outside a tabular/"
                f"aligned environment"
            ),
        )
    if re.search(r"(?<!\\)&", block.content):
        yield Finding(
            severity="warning",
            rule_id="stray-amp",
            line=block.start_line,
            col=block.start_col,
            block_index=block.index,
            message=(
                f"bare '&' in math block #{block.index} outside a tabular/"
                f"aligned environment"
            ),
        )


def _check_forbidden_delimiters(text: str) -> Iterator[Finding]:
    r"""Flag ``\(...\)`` and ``\[...\]`` math delimiters anywhere in the
    document. These do not render in GitHub markdown preview; the
    project standard is ``$...$`` and ``$$...$$`` (see ``AGENTS.md``).
    """
    for match in re.finditer(r"\\\(|\\\)|\\\[|\\\]", text):
        line = text.count("\n", 0, match.start()) + 1
        col = match.start() - (text.rfind("\n", 0, match.start()) + 1) + 1
        yield Finding(
            severity="error",
            rule_id="forbidden-delim",
            line=line,
            col=col,
            block_index=None,
            message=(
                f"forbidden math delimiter {match.group()!r}; use $...$ "
                f"or $$...$$ instead"
            ),
        )


def _check_dollar_balance(text: str) -> Iterator[Finding]:
    """Flag an odd number of effective ``$`` delimiters in the document.

    Treats ``$$`` as a single token and skips ``\\$`` escapes. Code fences
    are assumed already blanked by the caller.
    """
    i = 0
    n = len(text)
    count = 0
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == "$":
            if i + 1 < n and text[i + 1] == "$":
                count += 1
                i += 2
                continue
            count += 1
            i += 1
            continue
        i += 1
    if count % 2 != 0:
        yield Finding(
            severity="error",
            rule_id="dollar-balance",
            line=1,
            col=1,
            block_index=None,
            message=(
                f"unbalanced math delimiters: {count} effective '$' tokens "
                f"(should be even)"
            ),
        )


def verify_text(text: str) -> list[Finding]:
    """Run all lexer rules on a markdown source string.

    Parameters
    ----------
    text : str
        Markdown source. The interior of ```` ```mermaid ```` and
        ```` ```tikz ```` fences is skipped (Mermaid labels are allowed
        to contain Unicode math per ``AGENTS.md``; raw TikZ fences are
        intentionally not checked).

    Returns
    -------
    list of Finding
        Findings sorted by line then column.
    """
    stripped = _strip_fenced_blocks(text)
    stripped = _strip_code_fences(stripped)

    findings: list[Finding] = []
    findings.extend(_check_forbidden_delimiters(stripped))
    findings.extend(_check_dollar_balance(stripped))
    for block in _iter_math_blocks(stripped):
        findings.extend(_check_braces(block))
        findings.extend(_check_left_right(block))
        findings.extend(_check_begin_end(block))
        findings.extend(_check_unicode_math(block))
        findings.extend(_check_stray_tabular_tokens(block))
    findings.sort(key=lambda f: (f.line, f.col, f.rule_id))
    return findings


def _format_human(findings: list[Finding], source_label: str) -> str:
    if not findings:
        return f"{source_label}: clean (no LaTeX issues found)"
    lines = [f"{source_label}: {len(findings)} finding(s)"]
    for f in findings:
        block = f" [block #{f.block_index}]" if f.block_index is not None else ""
        lines.append(
            f"  {f.severity.upper():7} {f.rule_id:18} line {f.line}:{f.col}{block}  {f.message}"
        )
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(
        prog="python -m tools.verify_latex",
        description="Lexer-only LaTeX verifier for PaperLab markdown files.",
    )
    parser.add_argument(
        "path",
        help="Path to a markdown file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON instead of human-readable text.",
    )
    args = parser.parse_args(argv)

    if args.path == "-":
        text = sys.stdin.read()
        label = "<stdin>"
    else:
        with open(args.path, "r", encoding="utf-8") as fh:
            text = fh.read()
        label = args.path

    findings = verify_text(text)

    if args.json:
        payload = {
            "source": label,
            "findings": [f.to_dict() for f in findings],
            "error_count": sum(1 for f in findings if f.severity == "error"),
            "warning_count": sum(1 for f in findings if f.severity == "warning"),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_format_human(findings, label))

    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
