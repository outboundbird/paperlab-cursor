---
name: ml-latex-verify
description: Defines the LaTeX verification protocol for PaperLab. Wraps `tools/verify_latex.py` (lexer v1) and specifies how the Latex-Verifier subagent reports findings to its caller (Tutor or Explainer in the inline gate, or the post-hoc hook for non-gated agents). Use when verifying, lexing, or checking LaTeX correctness in vault markdown files or in draft text held by another agent.
---

# ML LaTeX Verify Schema

## Purpose

This skill defines what the **Latex-Verifier** subagent does, how it is
invoked, and the structured contract it returns to its caller. The
verifier exists to catch the LaTeX failure modes the Tutor and Explainer
have produced in practice (unmatched braces, unpaired `\left`/`\right`,
mismatched `\begin`/`\end`, Unicode math leakage, forbidden `\(\)` and
`\[\]` delimiters) **before** they reach the user or the vault.

The verifier is a wrapper around `tools/verify_latex.py`. The tool does
the actual lexing; the subagent's job is to invoke the tool with the
right input, interpret its JSON output, and report back in a form the
calling agent can act on per-block.

## Two versions

| Version | Engine | Requires | Status |
|---|---|---|---|
| v1 | Pure-Python lexer (`tools/verify_latex.py`) | Python 3.10+ | **Active** |
| v2 | KaTeX strict-mode renderer | Node.js (Linux machine) | **TODO** |

v1 catches ~70% of real errors with zero dependencies. v2 will run the
actual KaTeX renderer for stronger guarantees and matches what Obsidian
actually renders. v2 is scheduled for the Linux machine; v1 is the only
engine on Windows.

## Two invocation modes

The verifier supports two modes; the calling agent picks one.

### Mode A — verify a file on disk

For the post-hoc hook and for any agent that has already written a
markdown file and wants to re-check it.

Input: an absolute or workspace-relative path to a `.md` file.

```bash
python -m tools.verify_latex <path> --json
```

### Mode B — verify a draft text held in memory

For the inline gate. The calling agent (Tutor or Explainer) has drafted
a response but has not emitted it yet; it passes the draft on stdin.

```bash
echo "<draft text>" | python -m tools.verify_latex - --json
```

In practice the calling agent invokes the Latex-Verifier subagent with
the draft as a string argument; the subagent writes that string to a
temporary file or pipes it to the CLI.

## What the tool checks

Eight rules across six families, all scoped to math blocks (`$...$` and
`$$...$$`) unless noted:

| Rule ID | Severity | Scope | Catches |
|---|---|---|---|
| `brace-balance` | error | math block | unmatched `{` / `}` |
| `left-right` | error | math block | `\left` without `\right` and vice versa |
| `begin-end` | error | math block | unmatched / mis-nested `\begin{X}` / `\end{X}` |
| `unicode-math` | error | math block | Unicode math chars (`θ`, `μ`, `Σ`, ...) — forbidden per `AGENTS.md` |
| `stray-newline` | warning | math block (outside tabular envs) | `\\` outside `array`/`align`/`matrix`/`cases`/... |
| `stray-amp` | warning | math block (outside tabular envs) | bare `&` outside the same envs |
| `forbidden-delim` | error | whole document | `\(...\)` and `\[...\]` — don't render in GitHub markdown |
| `dollar-balance` | error | whole document | odd number of `$` tokens (unterminated math) |

The contents of ```` ```mermaid ```` and ```` ```tikz ```` fenced blocks
are **excluded** from all checks. This is the `AGENTS.md` Mermaid
exception: Mermaid labels render as plain text/HTML and require Unicode
math characters for atomic symbols.

## Output schema

The tool emits a single JSON object when called with `--json`:

```json
{
  "source": "<path or '<stdin>'>",
  "findings": [
    {
      "severity": "error",
      "rule_id": "brace-balance",
      "line": 16,
      "col": 13,
      "block_index": 4,
      "message": "1 unclosed '{' in math block #4"
    }
  ],
  "error_count": 1,
  "warning_count": 0
}
```

Field semantics:

- `severity`: `error` blocks emission in the inline gate; `warning` does not.
- `rule_id`: stable identifier; the calling agent can branch on it.
- `line`, `col`: 1-indexed location in the source.
- `block_index`: 1-indexed math-block position when the finding is
  block-scoped, else `null` (used by `forbidden-delim` and
  `dollar-balance`).
- `message`: human-readable description.

Exit code: 0 if no errors; 1 if any `error`-severity finding.

## Subagent contract — what Latex-Verifier returns to its caller

When invoked as a subagent, the Latex-Verifier returns a structured
report the calling agent can act on without re-parsing the tool output.
The report is a single message in this shape:

```markdown
## LaTeX verification report

- source: <path or "draft">
- errors: <N>
- warnings: <M>

### Errors
- block #4, line 16: brace-balance — 1 unclosed '{'
- block #5, line 20: begin-end — \end{matrix} does not match \begin{align}
- whole doc, line 34: forbidden-delim — '\(' must be replaced with '$'

### Warnings
- block #7, line 30: stray-newline — '\\' outside tabular env

### Verdict
- **FAIL** (1+ errors)  |  **PASS** (no errors)
```

The verdict line is mandatory. The calling agent uses it as the
gate-decision signal.

## Scope boundaries

The Latex-Verifier:

- **Does not** edit any file. It is read-only.
- **Does not** invoke other subagents.
- **Does not** explain LaTeX or suggest fixes beyond what the tool's
  `message` field says. Fixing is the caller's responsibility.
- **Does not** verify content correctness (is the equation
  mathematically right?). Only syntactic / structural correctness.
- **Does not** verify rendering in any specific environment beyond what
  the lexer rules cover. v2 (KaTeX) will tighten this.

## Where this fits in the verifier system

The Latex-Verifier is one of two verifier subagents (the other is the
`citation-verifier`). Both are invoked by the inline gate in Tutor and
Explainer **before** content reaches the user, and by the post-hoc
hook on vault `*.md` writes from any future agent that does not gate
inline. See `AGENTS.md` § "Verifier system" for the full architecture.

## Self-checks (verifier subagent, at end of its turn)

- Did I report the verdict line (`PASS` or `FAIL`)?
- Did I list every error and warning the tool reported, with `block_index`
  / line numbers intact?
- Did I avoid suggesting fixes the tool did not name?
- Did I avoid editing the source file?
