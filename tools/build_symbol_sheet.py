"""Build per-entry visualizer symbol tiles (graphviz auto-render).

For each entry in ``DICTIONARY.md`` that has a registered renderer below,
emit one PNG tile + one SVG tile under
``.cursor/skills/ml-visualization/symbols/auto/`` showing the canonical
drawing.

User-drawn replacement tiles live in the parent ``symbols/`` directory
and are referenced from individual ``DICTIONARY.md`` rows via inline
markdown image syntax (``![](symbols/<file>.png)``). When such a
reference exists, the PDF builder uses the user's PNG instead of the
auto-rendered tile in this folder. The two directories are kept separate
so a user-drawn ``symbols/E1.png`` cannot be overwritten by an auto-render
for the same entry ID.

The composite reference card lives in ``DICTIONARY.pdf`` and is built by
``tools/build_dictionary_pdf.py``, which selects per row between the
user-drawn tile (preferred) and the auto-rendered tile in ``auto/``.

Run:

    python -m tools.build_symbol_sheet

Outputs:

    .cursor/skills/ml-visualization/symbols/auto/E1.png
    .cursor/skills/ml-visualization/symbols/auto/E1.svg
    .cursor/skills/ml-visualization/symbols/auto/...

Design notes
------------

- Each tile is a tiny graphviz graph (1-2 nodes + maybe an arrow) sized for
  a card-like ~280x180 px output.
- The renderer registry is **hand-maintained** for v0.1. When you add a new
  entry to ``DICTIONARY.md``, add a matching ``_render_<id>`` function here.
  The script warns about (a) dictionary entries with no renderer and (b)
  registered renderers with no dictionary entry — so the two stay in sync.
- This is the schema-v0.1 approach: list-level sync between dictionary and
  tiles, drawing-level hand-coded. A future v0.2 upgrade could store the
  recipe declaratively in ``DICTIONARY.md`` and remove this script's
  drawing code.
"""

from __future__ import annotations

import re
import subprocess
from typing import Callable

from tools.paths import graphviz_dot, repo_root


SYMBOLS_DIR = repo_root() / ".cursor" / "skills" / "ml-visualization" / "symbols"
AUTO_DIR = SYMBOLS_DIR / "auto"
DICT_PATH = repo_root() / ".cursor" / "skills" / "ml-visualization" / "DICTIONARY.md"


# ---------------------------------------------------------------------------
# Shared graphviz preamble: fonts, sizing, no graph border.
# ---------------------------------------------------------------------------

FONT = "Segoe UI,DejaVu Sans,sans-serif"

PREAMBLE = f"""
    rankdir = LR;
    bgcolor = "white";
    pad = "0.15";
    margin = "0.05";
    fontname = "{FONT}";
    fontsize = 10;
    label = "";
    node [fontname="{FONT}", fontsize=10, style="filled", penwidth=1.0];
    edge [fontname="{FONT}", fontsize=9, color="#444", penwidth=1.0];
"""


def _emit(tile_id: str, body: str) -> None:
    """Compile a single tile from a graphviz body string into ``AUTO_DIR``."""
    src = f'digraph "{tile_id}" {{{PREAMBLE}{body}\n}}\n'
    dot_file = AUTO_DIR / f"{tile_id}.dot"
    png_file = AUTO_DIR / f"{tile_id}.png"
    svg_file = AUTO_DIR / f"{tile_id}.svg"
    dot_file.write_text(src, encoding="utf-8")
    dot_exe = str(graphviz_dot())
    subprocess.run([dot_exe, "-Tpng", "-Gdpi=140", str(dot_file), "-o", str(png_file)], check=True)
    subprocess.run([dot_exe, "-Tsvg", str(dot_file), "-o", str(svg_file)], check=True)


# ---------------------------------------------------------------------------
# Renderer registry. Each function returns the *body* of a graphviz digraph
# (no enclosing braces, no preamble) that draws the entry's canonical glyph.
# Tiles include a small tag label so the sheet reads as a reference card.
# ---------------------------------------------------------------------------


# ── Entities ───────────────────────────────────────────────────────────────


def _render_E1() -> str:
    return """
    n [label=<Z<SUB>X</SUB><SUP>(l)</SUP><BR/><FONT POINT-SIZE="8">E1 vector</FONT>>,
       shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    """


def _render_E2() -> str:
    return """
    n [label=<r<BR/><FONT POINT-SIZE="8">E2 scalar</FONT>>,
       shape=circle, fillcolor="#fff3cd", color="#a07a00", width=0.6, fixedsize=true];
    """


def _render_E4() -> str:
    return """
    n [label=<p(z)<BR/><FONT POINT-SIZE="8">E4 distribution</FONT>>,
       shape=ellipse, fillcolor="#f8d7da", color="#a23b3b"];
    """


def _render_E5() -> str:
    return """
    cond [label=<P(Z | A, X)<BR/><FONT POINT-SIZE="8">E5 conditional</FONT>>,
          shape=ellipse, fillcolor="#f8d7da", color="#a23b3b"];
    A [label="A", shape=box, fillcolor="#d1e7dd", color="#1c5e3c"];
    X [label="X", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    A -> cond [label="R1"];
    X -> cond [label="R1"];
    """


def _render_E6() -> str:
    return """
    n [label=<( μ | σ<SUP>2</SUP> )<BR/><FONT POINT-SIZE="8">E6 / A23 split</FONT>>,
       shape=box, fillcolor="#ffe9b3", color="#a64b00", peripheries=2];
    """


def _render_E7() -> str:
    return """
    n [label=<θ<BR/><FONT POINT-SIZE="8">E7 params</FONT>>,
       shape=box, fillcolor="#e9ecef", color="#495057", style="filled"];
    """


def _render_E8() -> str:
    return """
    n [label=<𝒟<BR/><FONT POINT-SIZE="8">E8 dataset</FONT>>,
       shape=cylinder, fillcolor="#e9ecef", color="#495057"];
    """


def _render_E9() -> str:
    return """
    n [label=<{ xᵢ }<SUB>i=1..M</SUB><BR/><FONT POINT-SIZE="8">E9 minibatch</FONT>>,
       shape=box, fillcolor="#e9ecef", color="#495057"];
    """


def _render_E10() -> str:
    return """
    n [label=<xᵢ<BR/><FONT POINT-SIZE="8">E10 sample</FONT>>,
       shape=circle, fillcolor="#cfe2ff", color="#0d6efd", width=0.5, fixedsize=true];
    """


def _render_E11() -> str:
    return """
    s1 [label="s₁", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s2 [label="s₂", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s3 [label="s₃", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s1 -> s2;
    s2 -> s3;
    cap [label=<E11 trajectory>, shape=plain];
    s3 -> cap [style=invis];
    """


def _render_E12() -> str:
    return """
    subgraph cluster_loop {
        label = <layer l<BR/><FONT POINT-SIZE="8">E12 / A10 loop frame</FONT>>;
        style = "dashed";
        color = "#888";
        inner [label="...", shape=box, fillcolor="white", color="#888"];
    }
    """


def _render_E13() -> str:
    return """
    a [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.35, fixedsize=true];
    b [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.35, fixedsize=true];
    c [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.35, fixedsize=true];
    cap [label=<E13 graph node>, shape=plain];
    a -> b [arrowhead=none];
    b -> c [arrowhead=none];
    c -> cap [style=invis];
    """


def _render_E14() -> str:
    return """
    a [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.3, fixedsize=true];
    b [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.3, fixedsize=true];
    c [label="", shape=circle, fillcolor="#bfe0d3", color="#1c5e3c", width=0.3, fixedsize=true];
    cap [label=<E14 edge subset>, shape=plain];
    a -> b [arrowhead=none, penwidth=2.0, color="#1c5e3c"];
    b -> c [arrowhead=none, style=dashed, color="#888"];
    c -> cap [style=invis];
    """


def _render_E18() -> str:
    return """
    n [label=<ε<BR/><FONT POINT-SIZE="8">E18 noise</FONT>>,
       shape=circle, fillcolor="#f5d6f5", color="#7a3a7a", width=0.6, fixedsize=true];
    """


def _render_E19() -> str:
    return """
    n [label=<f(x, y)<BR/><FONT POINT-SIZE="8">E19 critic</FONT>>,
       shape=box, fillcolor="#e9ecef", color="#495057", style="filled,bold"];
    """


def _render_E22() -> str:
    return """
    n [label=<π(a | s)<BR/><FONT POINT-SIZE="8">E22 policy</FONT>>,
       shape=trapezium, fillcolor="#fff3cd", color="#a07a00"];
    """


# ── Relations ──────────────────────────────────────────────────────────────


def _render_R1() -> str:
    return """
    cond [label="B", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    out  [label="A", shape=ellipse, fillcolor="#f8d7da", color="#a23b3b"];
    cond -> out [label="R1: A | B"];
    """


def _render_R2() -> str:
    return """
    s1 [label="A_t",   shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s2 [label="A_t+1", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s1 -> s2 [label="R2: next"];
    """


def _render_R3() -> str:
    return """
    f [label="f", shape=box, fillcolor="#e9ecef", color="#495057"];
    p [label="θ", shape=box, fillcolor="#e9ecef", color="#495057"];
    p -> f [label="R3: param-by", style=dotted, arrowhead=none];
    """


def _render_R6() -> str:
    return """
    a [label="A", shape=plain];
    b [label="B", shape=plain];
    a -> b [label="R6: A ≤ B", arrowhead=none, color="#444"];
    """


def _render_R8() -> str:
    return """
    a [label="forward", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    b [label="target",  shape=box, fillcolor="#e9ecef", color="#495057"];
    a -> b [label="R8: stop-grad", color="#888", arrowtail=tee, dir=both];
    """


def _render_R10() -> str:
    return """
    v   [label="v", shape=circle, fillcolor="#0d6efd", color="#0d6efd", fontcolor="white", width=0.5, fixedsize=true];
    h1a [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.3, fixedsize=true];
    h1b [label="", shape=circle, fillcolor="#d1e7dd", color="#1c5e3c", width=0.3, fixedsize=true];
    h2  [label="", shape=circle, fillcolor="#bfe0d3", color="#1c5e3c", width=0.3, fixedsize=true];
    cap [label=<R10 hop rings>, shape=plain];
    v   -> h1a [label="t=1", arrowhead=none, style=dashed];
    v   -> h1b [arrowhead=none, style=dashed];
    h1b -> h2  [label="t=2", arrowhead=none, style=dashed];
    h2  -> cap [style=invis];
    """


# ── Actions ────────────────────────────────────────────────────────────────


def _render_A1() -> str:
    return """
    src [label=<p(z)<BR/><FONT POINT-SIZE="8">distribution</FONT>>,
         shape=ellipse, fillcolor="#f8d7da", color="#a23b3b"];
    dst [label=<z<SUB>i</SUB><BR/><FONT POINT-SIZE="8">sample</FONT>>,
         shape=circle, fillcolor="#cfe2ff", color="#0d6efd", width=0.5, fixedsize=true];
    src -> dst [label="A1: sample", color="#a23b3b", penwidth=1.4];
    """


def _render_A2() -> str:
    return """
    src [label="𝒟", shape=cylinder, fillcolor="#e9ecef", color="#495057"];
    dst [label=<{ xᵢ }<SUB>i=1..M</SUB>>, shape=box, fillcolor="#e9ecef", color="#495057"];
    src -> dst [label="A2: draw"];
    """


def _render_A5() -> str:
    return """
    stats [label=<( μ, σ<SUP>2</SUP> )>, shape=box, fillcolor="#ffe9b3", color="#a64b00", peripheries=2];
    out   [label="z", shape=circle, fillcolor="#cfe2ff", color="#0d6efd", width=0.5, fixedsize=true];
    eps   [label="ε", shape=circle, fillcolor="#f5d6f5", color="#7a3a7a", width=0.5, fixedsize=true];
    stats -> out [label="A5: reparameterize", color="#a05a00", penwidth=1.4];
    eps   -> out [label="(noise)", style=dashed, color="#7a3a7a", constraint=false];
    """


def _render_A6() -> str:
    return """
    a [label="x", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    b [label="Wx + b", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    a -> b [label="A6: transform"];
    """


def _render_A7() -> str:
    return """
    x1 [label="x₁", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    x2 [label="x₂", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    x3 [label="x₃", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    agg [label=<<FONT POINT-SIZE="20">Σ</FONT><BR/><FONT POINT-SIZE="8">A7 aggregate</FONT>>,
         shape=circle, fillcolor="#e2e3e5", color="#495057"];
    x1 -> agg;
    x2 -> agg;
    x3 -> agg;
    """


def _render_A11() -> str:
    return """
    s1 [label="s₁", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s2 [label="s₂", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s3 [label="s₃", shape=box, fillcolor="#cfe2ff", color="#0d6efd"];
    s4 [label="...", shape=plain];
    s1 -> s2 [label="A11"];
    s2 -> s3 [label="(roll fwd)"];
    s3 -> s4;
    """


def _render_A12() -> str:
    return """
    p [label="p", shape=ellipse, fillcolor="#f8d7da", color="#a23b3b"];
    q [label="q", shape=ellipse, fillcolor="#e9ecef", color="#888"];
    p -> q [label="A12: compare\\n(KL)", arrowhead=none];
    """


def _render_A14() -> str:
    return """
    a [label="A", shape=plain];
    b [label="B", shape=plain];
    a -> b [label="A14: bound\\n(A ≤ B)", arrowhead=none];
    """


def _render_A17() -> str:
    return """
    n [label=<min<SUB>φ</SUB>  ℒ(φ)<BR/><FONT POINT-SIZE="8">A17 optimize</FONT>>,
       shape=box, fillcolor="#fff3cd", color="#a07a00"];
    """


def _render_A19() -> str:
    return """
    a [label="loss", shape=box, fillcolor="#f8d7da", color="#a23b3b"];
    b [label="θ",    shape=box, fillcolor="#e9ecef", color="#495057"];
    a -> b [label="A19: propagate ∇", style=dashed, color="#a23b3b"];
    """


def _render_A20() -> str:
    return """
    n [label=<θ ❄<BR/><FONT POINT-SIZE="8">A20 freeze</FONT>>,
       shape=box, fillcolor="#e9ecef", color="#495057", style="filled,dashed"];
    """


def _render_A23() -> str:
    return """
    n [label=<( μ | σ<SUP>2</SUP> )<BR/><FONT POINT-SIZE="8">A23 split</FONT>>,
       shape=box, fillcolor="#ffe9b3", color="#a64b00", peripheries=2];
    """


def _render_A27() -> str:
    return """
    s1 [label="rₜ",   shape=box, fillcolor="#fff3cd", color="#a07a00"];
    s2 [label="rₜ₊₁", shape=box, fillcolor="#fff3cd", color="#a07a00"];
    sk [label=<v<SUB>ψ</SUB>(sₜ₊ₖ)>, shape=box, fillcolor="#e9ecef", color="#495057", style="filled,bold"];
    s1 -> s2;
    s2 -> sk [label="A27: bootstrap"];
    """


def _render_A26() -> str:
    return """
    r1 [label="r₁", shape=box, fillcolor="#fff3cd", color="#a07a00"];
    r2 [label="r₂", shape=box, fillcolor="#fff3cd", color="#a07a00"];
    r3 [label="r₃", shape=box, fillcolor="#fff3cd", color="#a07a00"];
    s  [label=<<FONT POINT-SIZE="20">Σ</FONT><BR/><FONT POINT-SIZE="8">A26 accumulate</FONT>>,
        shape=circle, fillcolor="#e2e3e5", color="#495057"];
    r1 -> s;
    r2 -> s;
    r3 -> s;
    """


# ---------------------------------------------------------------------------
# Registry: dictionary id -> (category, renderer).
# ---------------------------------------------------------------------------

RENDERERS: dict[str, tuple[str, Callable[[], str]]] = {
    # Entities
    "E1": ("Entity", _render_E1),
    "E2": ("Entity", _render_E2),
    "E4": ("Entity", _render_E4),
    "E5": ("Entity", _render_E5),
    "E6": ("Entity", _render_E6),
    "E7": ("Entity", _render_E7),
    "E8": ("Entity", _render_E8),
    "E9": ("Entity", _render_E9),
    "E10": ("Entity", _render_E10),
    "E11": ("Entity", _render_E11),
    "E12": ("Entity", _render_E12),
    "E13": ("Entity", _render_E13),
    "E14": ("Entity", _render_E14),
    "E18": ("Entity", _render_E18),
    "E19": ("Entity", _render_E19),
    "E22": ("Entity", _render_E22),
    # Relations
    "R1": ("Relation", _render_R1),
    "R2": ("Relation", _render_R2),
    "R3": ("Relation", _render_R3),
    "R6": ("Relation", _render_R6),
    "R8": ("Relation", _render_R8),
    "R10": ("Relation", _render_R10),
    # Actions
    "A1": ("Action", _render_A1),
    "A2": ("Action", _render_A2),
    "A5": ("Action", _render_A5),
    "A6": ("Action", _render_A6),
    "A7": ("Action", _render_A7),
    "A11": ("Action", _render_A11),
    "A12": ("Action", _render_A12),
    "A14": ("Action", _render_A14),
    "A17": ("Action", _render_A17),
    "A19": ("Action", _render_A19),
    "A20": ("Action", _render_A20),
    "A23": ("Action", _render_A23),
    "A26": ("Action", _render_A26),
    "A27": ("Action", _render_A27),
}


# ---------------------------------------------------------------------------
# Dictionary parsing for sync checks.
# ---------------------------------------------------------------------------


def _parse_dictionary_ids() -> set[str]:
    """Return the set of entry IDs present in DICTIONARY.md (E1, R1, A1, ...).

    Parses the markdown table rows by looking for cells of the form
    ``| E12 |`` / ``| R6 |`` / ``| A7 |`` at the start of a row.
    """
    text = DICT_PATH.read_text(encoding="utf-8")
    ids = set()
    for line in text.splitlines():
        m = re.match(r"\|\s*([EAR]\d+)\s*\|", line)
        if m:
            ids.add(m.group(1))
    return ids


def _check_sync() -> None:
    """Warn (don't fail) about drift between DICTIONARY.md and renderers."""
    dict_ids = _parse_dictionary_ids()
    registered = set(RENDERERS)

    missing_renderer = dict_ids - registered
    orphan_renderer = registered - dict_ids

    if missing_renderer:
        print(
            f"INFO: {len(missing_renderer)} dictionary entries have no symbol "
            f"renderer yet (atlas covers {len(registered)}/{len(dict_ids)}): "
            f"{', '.join(sorted(missing_renderer))}"
        )
    if orphan_renderer:
        print(
            f"WARNING: {len(orphan_renderer)} registered renderers have no "
            f"matching dictionary entry: {', '.join(sorted(orphan_renderer))}"
        )


def _id_sort_key(entry_id: str) -> tuple[str, int]:
    """Sort 'E1', 'E10' as ('E', 1) and ('E', 10)."""
    m = re.match(r"([EAR])(\d+)", entry_id)
    return (m.group(1), int(m.group(2))) if m else (entry_id, 0)


def main() -> None:
    SYMBOLS_DIR.mkdir(parents=True, exist_ok=True)
    AUTO_DIR.mkdir(parents=True, exist_ok=True)
    _check_sync()

    for entry_id in sorted(RENDERERS, key=_id_sort_key):
        _, render = RENDERERS[entry_id]
        body = render()
        _emit(entry_id, body)
        print(f"wrote {AUTO_DIR / (entry_id + '.png')}")


if __name__ == "__main__":
    main()
