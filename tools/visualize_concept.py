"""Visualizer v2 — concept-picture renderer.

Render a *concept picture* by composing dictionary entries declared in a
small YAML picture-spec. This is the deterministic half of the v2
pipeline: an agent (or a human, for now) writes the spec; this tool turns
it into a PNG via graphviz.

The dictionary is consulted as a **style guide**, not a clip-art library:
each ``dict_id`` resolves to an inline graphviz shape (box / ellipse /
trapezium / …) with the project's per-category palette. The role-specific
label is rendered *inside* that shape at the picture's natural scale.

User-drawn ``symbols/<id>.png`` files exist only as the visual definition
of each dictionary atom inside ``DICTIONARY.pdf``. They are NEVER pasted
into concept pictures. See ``.cursor/skills/ml-visualization/SKILL.md``
section "What the dictionary is (and what it is not)".

Picture-spec schema (YAML)
--------------------------

::

    title: "GIB §3.1 — Panel B"        # str, used as graphviz graph label
    rankdir: LR                         # optional, default LR (or TB / BT / RL)
    nodes:
      - id: Zx_prev                     # picture-local id (unique in this spec)
        dict_id: E1                     # dictionary entry; resolves glyph
        label: "Z_X^(l-1)"              # paper-specific label drawn on the node
      - id: P_ZA
        dict_id: E5
        label: "P(Z_A^(l) | A, Z_X^(l-1))"
    edges:
      - src: Zx_prev                    # node id (above) or "<dict_id>" shorthand
        dst: P_ZA
        dict_id: R1                     # arrow style derived from this entry
        label: "R1"                     # optional extra annotation
    clusters:                           # optional E12-style frames
      - id: layer_frame
        label: "layer l = 1..L  [E12/A10: iterate]"
        contains: [Zx_prev, P_ZA, ...]

Glyph resolution for a node's ``dict_id``
-----------------------------------------

Each ``dict_id`` maps to an inline graphviz shape in ``_NODE_STYLE`` below:
shape, fill colour, stroke colour, peripheries, line style. The role-specific
``label`` is rendered inside the shape via the normal ``label=`` attribute.
Entries without an explicit style fall back to ``_FALLBACK_NODE_STYLE``
(blue box) so the picture still composes; the lint pass in
``figure-verifier`` flags unknown ``dict_id``s.

Edge styling priority for a ``dict_id``
---------------------------------------

Edges don't have a visual glyph the way nodes do — they have a *style*.
This first slice uses a small hardcoded style table (solid / dashed /
dotted, color, arrowhead) keyed on the edge's dict_id. Future revisions
can read the style from the dictionary's Symbolic-representation column
when a more declarative grammar is in place.

Run
---

::

    python -m tools.visualize_concept <spec.yaml> <out.png>

Both paths are absolute or relative to the repo root.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tools.paths import graphviz_dot, repo_root, vault_path


SKILL_DIR = repo_root() / ".cursor" / "skills" / "ml-visualization"
DICT_PATH = SKILL_DIR / "DICTIONARY.md"


# ---------------------------------------------------------------------------
# Dictionary parsing — entry IDs and canonical names only.
# ---------------------------------------------------------------------------


TABLE_ROW_RE = re.compile(r"^\|\s*([EAR]\d+)\s*\|(.+)\|\s*$")


@dataclass
class DictEntry:
    """A single dictionary row, parsed enough for the renderer."""

    entry_id: str
    canonical: str
    aliases: str
    symbolic: str

    @property
    def category(self) -> str:
        """``"Entity"`` / ``"Relation"`` / ``"Action"`` derived from the ID prefix."""
        return {"E": "Entity", "R": "Relation", "A": "Action"}[self.entry_id[0]]


def _load_dictionary() -> dict[str, DictEntry]:
    """Parse ``DICTIONARY.md`` into a mapping ``entry_id -> DictEntry``.

    Used for validation (catching unknown ``dict_id`` references). The
    renderer reads styles from the in-Python ``_NODE_STYLE`` / ``_EDGE_STYLE``
    tables below, not from the dictionary's prose; the dictionary is the
    source of truth for the *list* of entries, not the rendered style.
    """
    text = DICT_PATH.read_text(encoding="utf-8")
    entries: dict[str, DictEntry] = {}
    for line in text.splitlines():
        m = TABLE_ROW_RE.match(line)
        if not m:
            continue
        entry_id = m.group(1).strip()
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 3:
            continue
        canonical, aliases, symbolic = cells[0], cells[1], cells[2]
        entries[entry_id] = DictEntry(
            entry_id=entry_id,
            canonical=canonical,
            aliases=aliases,
            symbolic=symbolic,
        )
    return entries


# ---------------------------------------------------------------------------
# Picture-spec schema (loaded from YAML).
# ---------------------------------------------------------------------------


@dataclass
class SpecNode:
    id: str
    dict_id: str
    label: str = ""
    legend_context: str = ""  # short paper-language phrase for the legend


@dataclass
class SpecEdge:
    src: str
    dst: str
    dict_id: str = ""
    label: str = ""
    legend_context: str = ""  # short paper-language phrase for the legend


@dataclass
class SpecCluster:
    id: str
    label: str = ""
    contains: list[str] = field(default_factory=list)


@dataclass
class LegendOverride:
    """Optional per-``dict_id`` legend row override from the spec's
    top-level ``legend:`` block. Either field may be empty to keep the
    auto-derived value (label from first-occurrence, context from the
    same node/edge's ``legend_context``)."""

    dict_id: str
    label: str = ""
    legend_context: str = ""


@dataclass
class PictureSpec:
    title: str = ""
    rankdir: str = "LR"
    nodes: list[SpecNode] = field(default_factory=list)
    edges: list[SpecEdge] = field(default_factory=list)
    clusters: list[SpecCluster] = field(default_factory=list)
    legend_overrides: list[LegendOverride] = field(default_factory=list)
    # Optional output naming hints. When the CLI `out` argument is omitted,
    # ``output`` (a bare name or filename) is resolved against
    # ``vault_path(slug, "figures/")`` to produce the final PNG path. The
    # naming convention itself (e.g. ``<concept>`` or ``<slug>-<pseudocode>``)
    # is the caller's responsibility — see SKILL.md "Output naming".
    slug: str | None = None
    output: str | None = None


def _load_spec(path: Path) -> PictureSpec:
    """Parse a picture-spec YAML into a ``PictureSpec``.

    Raises
    ------
    ValueError
        If the YAML is missing required fields or contains unknown ``dict_id``
        references that the dictionary check (in ``main``) will then flag.
    """
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    spec = PictureSpec(
        title=raw.get("title", ""),
        rankdir=raw.get("rankdir", "LR"),
        slug=raw.get("slug"),
        output=raw.get("output"),
    )
    for n in raw.get("nodes", []) or []:
        if "id" not in n or "dict_id" not in n:
            raise ValueError(f"Node missing required keys (id, dict_id): {n}")
        spec.nodes.append(SpecNode(
            id=n["id"], dict_id=n["dict_id"],
            label=n.get("label", ""),
            legend_context=n.get("legend_context", ""),
        ))
    for e in raw.get("edges", []) or []:
        if "src" not in e or "dst" not in e:
            raise ValueError(f"Edge missing required keys (src, dst): {e}")
        spec.edges.append(SpecEdge(
            src=e["src"], dst=e["dst"],
            dict_id=e.get("dict_id", ""), label=e.get("label", ""),
            legend_context=e.get("legend_context", ""),
        ))
    for c in raw.get("clusters", []) or []:
        if "id" not in c:
            raise ValueError(f"Cluster missing required key (id): {c}")
        spec.clusters.append(SpecCluster(
            id=c["id"], label=c.get("label", ""), contains=list(c.get("contains", []))
        ))
    for lo in raw.get("legend", []) or []:
        if "dict_id" not in lo:
            raise ValueError(f"Legend override missing dict_id: {lo}")
        spec.legend_overrides.append(LegendOverride(
            dict_id=lo["dict_id"],
            label=lo.get("label", ""),
            legend_context=lo.get("legend_context", ""),
        ))
    return spec


# ---------------------------------------------------------------------------
# DOT emission.
# ---------------------------------------------------------------------------


FONT = "Segoe UI,DejaVu Sans,sans-serif"


# Per-``dict_id`` inline node style. Each value is a partial set of graphviz
# node attributes; together with the role-specific ``label`` (drawn inside
# the node) this is what the dictionary entry resolves to in a rendered
# picture. Palette is consistent across categories:
#   - Entities (E*) use the project's vector/distribution/param palette.
#   - Relations (R*) never appear as nodes — they are edge styles below.
#   - Actions  (A*) rarely appear as nodes — they are edge styles below.
# Missing entries fall back to ``_FALLBACK_NODE_STYLE`` (blue box).
# Each style honours its dictionary "Symbolic representation" recipe as
# closely as plain graphviz primitives allow. Where the recipe demands a
# pictorial element graphviz can't draw natively (e.g., E1's "vertical
# column of small cells", E8's stack of cards), the closest shape is
# chosen and the recipe is honoured at the *category* level (e.g., E1 is
# a chip-like rounded blue rectangle; the actual cell-count nuance is
# carried by the math label inside the node).
_NODE_STYLE: dict[str, dict[str, str]] = {
    # E1 vector — "vertical column of small cells (cell-column chip)".
    # Mrecord shape with the label as a single cell gives a rounded-corner
    # chip with a visible internal cell boundary.
    "E1": {"shape": "Mrecord", "fillcolor": "#cfe2ff", "color": "#0d6efd",
           "style": "filled"},
    # E2 scalar — "small filled disc".
    "E2": {"shape": "circle", "fillcolor": "#fff3cd", "color": "#a07a00",
           "width": "0.5", "fixedsize": "true"},
    # E3 tensor / image — "square or rectangle with optional grid".
    "E3": {"shape": "box3d", "fillcolor": "#cfe2ff", "color": "#0d6efd"},
    # E4 distribution — "smooth density curve / histogram"; ellipse is the
    # canonical density silhouette in node-graph land.
    "E4": {"shape": "ellipse", "fillcolor": "#f8d7da", "color": "#a23b3b"},
    # E5 conditional distribution — "distribution shape sitting inside a
    # node, with incoming arrows from the conditioning variables".
    "E5": {"shape": "ellipse", "fillcolor": "#f8d7da", "color": "#a23b3b",
           "penwidth": "1.6"},
    # E6 sufficient statistics (mu, sigma) — "a vector chip split into two
    # named halves". Double-bordered chip suggests the split.
    "E6": {"shape": "Mrecord", "fillcolor": "#ffe9b3", "color": "#a64b00",
           "peripheries": "2"},
    # E7 parameter set — "small square with a hat or color code; attached
    # via thin line (not arrow)" → dashed-stroke square; the "thin line"
    # part is handled by R3 (parameterised-by) being a dotted edge.
    "E7": {"shape": "box", "fillcolor": "#e9ecef", "color": "#495057",
           "style": "filled,dashed"},
    # E8 dataset — "stack of cards or labeled bin".
    "E8": {"shape": "cylinder", "fillcolor": "#e9ecef", "color": "#495057"},
    # E9 minibatch — "small cluster of sample markers"; folder-like.
    "E9": {"shape": "folder", "fillcolor": "#e9ecef", "color": "#495057"},
    # E10 sample — "single marker (dot, tagged cell, highlighted node)".
    "E10": {"shape": "circle", "fillcolor": "#cfe2ff", "color": "#0d6efd",
            "width": "0.4", "fixedsize": "true"},
    # E11 trajectory / sequence — "horizontal chain of entities"; when used
    # as a single node, a tagged box stands in.
    "E11": {"shape": "box", "fillcolor": "#cfe2ff", "color": "#0d6efd"},
    # E13 graph node — "a filled circle".
    "E13": {"shape": "circle", "fillcolor": "#d1e7dd", "color": "#1c5e3c",
            "width": "0.4", "fixedsize": "true"},
    # E14 graph edge / adjacency — "a line connecting two nodes". When
    # used as an entity (e.g., the adjacency matrix A, the sampled Z_A),
    # we draw it as a green square that visually echoes E13's palette.
    "E14": {"shape": "box", "fillcolor": "#d1e7dd", "color": "#1c5e3c"},
    # E15 candidate set / neighborhood — "dashed ring around an anchor".
    "E15": {"shape": "ellipse", "fillcolor": "#d1e7dd", "color": "#1c5e3c",
            "style": "filled,dashed"},
    # E16 learnable weight matrix — "small grid (rows x cols)".
    "E16": {"shape": "box", "fillcolor": "#cfe2ff", "color": "#0d6efd",
            "style": "filled,bold"},
    # E18 noise variable — "small jittered marker or stylized epsilon disc".
    "E18": {"shape": "circle", "fillcolor": "#f5d6f5", "color": "#7a3a7a",
            "width": "0.5", "fixedsize": "true"},
    # E19 critic / energy function — "labeled black-box rectangle".
    "E19": {"shape": "box", "fillcolor": "#e9ecef", "color": "#495057",
            "style": "filled,bold"},
    # E20 recurrent state — "vector chip with a self-loop".
    "E20": {"shape": "Mrecord", "fillcolor": "#cfe2ff", "color": "#0d6efd"},
    # E21 reference distribution — "distribution shape rendered in grey or
    # ghost outline" — light grey ellipse.
    "E21": {"shape": "ellipse", "fillcolor": "#f0f0f0", "color": "#888"},
    # E22 controller / policy — "labeled trapezoid or rectangle".
    "E22": {"shape": "trapezium", "fillcolor": "#fff3cd", "color": "#a07a00"},
    # E23 terminal event / done flag — "small stop glyph (filled square or X)".
    "E23": {"shape": "octagon", "fillcolor": "#f8d7da", "color": "#a23b3b"},
}
_FALLBACK_NODE_STYLE = {
    "shape": "box", "fillcolor": "#cfe2ff", "color": "#0d6efd",
}


# Per-``dict_id`` edge style. Captures the relation's or action's visual
# idiom (solid vs dashed vs dotted, arrowhead, color, weight). Edges
# always carry a label so the dictionary tag stays visible.
_EDGE_STYLE: dict[str, dict[str, str]] = {
    # Relations — structural facts.
    "R1": {"color": "#444", "penwidth": "1.0"},
    "R2": {"color": "#444", "penwidth": "1.2"},
    "R3": {"style": "dotted", "arrowhead": "none", "color": "#666",
           "constraint": "false"},
    "R4": {"color": "#444", "arrowhead": "none"},
    "R6": {"arrowhead": "none", "color": "#444"},
    "R7": {"color": "#444", "arrowhead": "none", "style": "bold"},
    "R8": {"color": "#888", "arrowtail": "tee", "dir": "both"},
    "R10": {"style": "dashed", "color": "#888", "arrowhead": "none"},
    "R11": {"color": "#444"},
    "R12": {"color": "#444"},
    # Actions — verbs the algorithm performs.
    "A1": {"color": "#a23b3b", "penwidth": "1.4"},
    "A2": {"color": "#495057", "penwidth": "1.2"},
    "A3": {"color": "#0d6efd", "penwidth": "1.2"},
    "A4": {"color": "#0d6efd", "penwidth": "1.2"},
    "A5": {"color": "#a05a00", "penwidth": "1.4"},
    "A6": {"color": "#0d6efd", "penwidth": "1.2"},
    "A7": {"color": "#495057", "penwidth": "1.4"},
    "A8": {"color": "#a07a00", "penwidth": "1.2"},
    "A9": {"color": "#0d6efd", "penwidth": "1.2"},
    "A11": {"color": "#0d6efd", "penwidth": "1.2"},
    "A12": {"color": "#a23b3b", "arrowhead": "none"},
    "A14": {"color": "#444", "arrowhead": "none"},
    "A17": {"color": "#a07a00", "penwidth": "1.4"},
    "A18": {"color": "#a05a00", "penwidth": "1.2"},
    "A19": {"style": "dashed", "color": "#a23b3b"},
    "A20": {"color": "#888", "style": "dashed"},
    "A26": {"color": "#a07a00", "penwidth": "1.2"},
}
_FALLBACK_EDGE_STYLE = {"color": "#444"}


def _escape_dot_label(s: str) -> str:
    """Escape a string for use inside a graphviz double-quoted label."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _escape_html(s: str) -> str:
    """Escape a string for use inside a graphviz HTML-like label."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _mathify(label: str) -> str:
    """Translate LaTeX-ish ``_``/``^`` sub/superscript syntax into graphviz
    HTML ``<SUB>``/``<SUP>`` markup.

    Recognised grammar (left to right, single pass):

    - ``X_{...}`` / ``X^{...}`` — braced groups; recurses for nested math.
    - ``X_(...)`` / ``X^(...)`` — parenthesised groups; parens preserved
      in the rendered output (so ``Z_X^(l-1)`` keeps the ``(l-1)``).
    - ``X_a`` / ``X^a`` — single-char form (any non-whitespace char).

    Everything else is HTML-escaped. Newlines become ``<BR/>``.

    Examples
    --------
    >>> _mathify("Z_X^(l-1)")
    'Z<SUB>X</SUB><SUP>(l-1)</SUP>'
    >>> _mathify("Z_{X,v}^{(l)}")
    'Z<SUB>X,v</SUB><SUP>(l)</SUP>'
    >>> _mathify("P(Z_A^(l) | A, Z_X^(l-1))")
    'P(Z<SUB>A</SUB><SUP>(l)</SUP> | A, Z<SUB>X</SUB><SUP>(l-1)</SUP>)'
    """
    out: list[str] = []
    i = 0
    n = len(label)
    while i < n:
        ch = label[i]
        if ch == "\n":
            out.append("<BR/>")
            i += 1
            continue
        if ch in ("_", "^"):
            tag = "SUB" if ch == "_" else "SUP"
            if i + 1 < n and label[i + 1] == "{":
                end = label.find("}", i + 2)
                if end == -1:
                    out.append(_escape_html(ch))
                    i += 1
                    continue
                inner = label[i + 2:end]
                out.append(f"<{tag}>{_mathify(inner)}</{tag}>")
                i = end + 1
            elif i + 1 < n and label[i + 1] == "(":
                end = label.find(")", i + 2)
                if end == -1:
                    out.append(_escape_html(ch))
                    i += 1
                    continue
                inner = label[i + 1:end + 1]  # keep the parens
                out.append(f"<{tag}>{_escape_html(inner)}</{tag}>")
                i = end + 1
            elif i + 1 < n and not label[i + 1].isspace():
                out.append(f"<{tag}>{_escape_html(label[i + 1])}</{tag}>")
                i += 2
            else:
                out.append(_escape_html(ch))
                i += 1
        else:
            out.append(_escape_html(ch))
            i += 1
    return "".join(out)


# Shapes that graphviz cannot combine with HTML-like labels. When a
# node's style asks for one of these, the renderer swaps in a rounded
# filled box so the math notation still renders.
_HTML_INCOMPATIBLE_SHAPES = {"Mrecord", "record"}
_HTML_FALLBACK_SHAPE = "box"


def _resolve_node_style(dict_id: str) -> dict[str, str]:
    """Return a graphviz attribute dict for a node, with HTML-incompatible
    shapes swapped for a rounded filled box (so HTML labels render)."""
    style = dict(_NODE_STYLE.get(dict_id, _FALLBACK_NODE_STYLE))
    if style.get("shape") in _HTML_INCOMPATIBLE_SHAPES:
        style["shape"] = _HTML_FALLBACK_SHAPE
        existing = style.get("style", "filled")
        if "rounded" not in existing:
            style["style"] = f"{existing},rounded" if existing else "rounded"
    return style


def _node_attrs(node: SpecNode) -> str:
    """Return the attribute fragment ``[...]`` for a node line in the DOT source.

    The node label is rendered as a graphviz HTML-like label so that
    LaTeX-ish sub/superscripts (``Z_X^(l-1)``) come out as proper
    ``<SUB>``/``<SUP>`` text on the rendered PNG.
    """
    html_label = _mathify(node.label or node.id)
    style = _resolve_node_style(node.dict_id)
    parts = [f"label=<{html_label}>"]
    for k, v in style.items():
        parts.append(f'{k}="{v}"')
    return "[" + ", ".join(parts) + "]"


def _edge_attrs(edge: SpecEdge) -> str:
    style = _EDGE_STYLE.get(edge.dict_id, _FALLBACK_EDGE_STYLE)
    label_text = edge.label or ""
    parts: list[str] = []
    if label_text:
        parts.append(f"label=<{_mathify(label_text)}>")
    for k, v in style.items():
        parts.append(f'{k}="{v}"')
    return "[" + ", ".join(parts) + "]"


def _emit_legend(
    spec: PictureSpec, entries: dict[str, DictEntry], indent: str = "    "
) -> list[str]:
    """Emit a legend subgraph listing every distinct ``dict_id`` in the spec.

    Legend wording (per SKILL.md "Legend wording"):

    - Row text = ``<paper notation> — <context phrase>``, both sourced from
      the first occurrence of the ``dict_id`` in the spec (node or edge).
    - Paper notation = the first-occurring node/edge's ``label`` field,
      rendered through ``_mathify`` so sub/superscripts render.
    - Context phrase = the first-occurring node/edge's ``legend_context``
      field. If empty, the row shows only the paper notation.
    - The spec's optional top-level ``legend:`` block overrides either
      field per ``dict_id``.
    - Dictionary codes (``E14``, ``R1``, …) and the dictionary's canonical
      name never appear in the legend.

    The legend is rendered as a single HTML-table node pinned to the
    right of the canvas via ``rank="sink"`` (under ``rankdir=LR``) plus
    an invisible anchor edge added by ``_emit_dot``.
    """
    # Walk nodes then edges, in source order, capturing first-occurrence
    # paper notation + context phrase per dict_id.
    @dataclass
    class _LegendRow:
        dict_id: str
        kind: str  # "node" or "edge"
        label: str  # paper notation
        context: str

    rows_by_did: dict[str, _LegendRow] = {}
    order: list[str] = []

    for n in spec.nodes:
        if n.dict_id and n.dict_id not in rows_by_did:
            rows_by_did[n.dict_id] = _LegendRow(
                dict_id=n.dict_id, kind="node",
                label=n.label, context=n.legend_context,
            )
            order.append(n.dict_id)
    for e in spec.edges:
        if e.dict_id and e.dict_id not in rows_by_did:
            rows_by_did[e.dict_id] = _LegendRow(
                dict_id=e.dict_id, kind="edge",
                label=e.label, context=e.legend_context,
            )
            order.append(e.dict_id)

    # Apply spec-level legend overrides.
    for ov in spec.legend_overrides:
        if ov.dict_id not in rows_by_did:
            # Override references a dict_id not used in the picture; skip.
            continue
        if ov.label:
            rows_by_did[ov.dict_id].label = ov.label
        if ov.legend_context:
            rows_by_did[ov.dict_id].context = ov.legend_context

    if not order:
        return []

    html_rows: list[str] = []
    for did in order:
        row = rows_by_did[did]
        label_html = _mathify(row.label or did)
        context_html = _escape_html(row.context)
        # The two columns: a swatch / line cell, then the text.
        # Text cell shows "<label> — <context>"; if context is empty,
        # just "<label>".
        text_cell = label_html if not context_html else (
            f"{label_html} &#8212; {context_html}"
        )
        # v8 sizing — paired with the v8 figure styles in _emit_figure_dot.
        text_cell_sized = f'<FONT POINT-SIZE="36">{text_cell}</FONT>'
        if row.kind == "node":
            style = _resolve_node_style(did)
            fill = style.get("fillcolor", "#cfe2ff")
            stroke = style.get("color", "#0d6efd")
            html_rows.append(
                f'<TR>'
                f'<TD WIDTH="40" HEIGHT="24" FIXEDSIZE="TRUE" '
                f'BGCOLOR="{fill}" BORDER="1" COLOR="{stroke}"></TD>'
                f'<TD ALIGN="LEFT">{text_cell_sized}</TD>'
                f'</TR>'
            )
        else:
            style = _EDGE_STYLE.get(did, _FALLBACK_EDGE_STYLE)
            color = style.get("color", "#444")
            html_rows.append(
                f'<TR>'
                f'<TD WIDTH="40" HEIGHT="24" FIXEDSIZE="TRUE" '
                f'SIDES="B" BORDER="2" COLOR="{color}"></TD>'
                f'<TD ALIGN="LEFT">{text_cell_sized}</TD>'
                f'</TR>'
            )

    table = (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4" CELLPADDING="6">'
        '<TR><TD COLSPAN="2"><FONT POINT-SIZE="44"><B>Legend</B></FONT></TD></TR>'
        + "".join(html_rows)
        + '</TABLE>>'
    )

    out: list[str] = []
    out.append(
        f'{indent}{{ rank = "sink"; '
        f'legend_panel [shape=plaintext, label={table}]; }}'
    )
    return out


def _emit_figure_dot(spec: PictureSpec, entries: dict[str, DictEntry]) -> str:
    """Emit DOT for the figure ONLY (no legend) — v8 styling.

    Used by ``render_composed`` which then composes a standalone legend PNG
    horizontally with PIL. No 4:3 clamp; graphviz sizes the canvas from the
    content at the requested font scale.
    """
    lines: list[str] = []
    lines.append("digraph figure {")
    lines.append(f'    rankdir = {spec.rankdir};')
    lines.append('    bgcolor = "white";')
    lines.append(f'    fontname = "{FONT}";')
    lines.append('    fontsize = 56;')
    lines.append('    labelloc = "t";')
    lines.append('    dpi = 160;')
    lines.append('    newrank = true;')
    if spec.title:
        lines.append(f'    label = "{_escape_dot_label(spec.title)}";')
    lines.append('    nodesep = 0.5;')
    lines.append('    ranksep = 0.9;')
    lines.append(
        f'    node [fontname="{FONT}", fontsize=48, style="filled", penwidth=2.0];'
    )
    lines.append(
        f'    edge [fontname="{FONT}", fontsize=40, color="#444444", '
        'penwidth=2.0, arrowsize=1.2];'
    )
    lines.append("")

    in_cluster: set[str] = set()
    for cluster in spec.clusters:
        in_cluster.update(cluster.contains)

    for i, cluster in enumerate(spec.clusters):
        lines.append(f'    subgraph cluster_{i} {{')
        lines.append('        style = "dashed";')
        lines.append('        color = "#888";')
        lines.append('        penwidth = 2.0;')
        lines.append(f'        label = "{_escape_dot_label(cluster.label)}";')
        for node in spec.nodes:
            if node.id in cluster.contains:
                lines.append(f'        {node.id} {_node_attrs(node)};')
        lines.append('    }')

    for node in spec.nodes:
        if node.id not in in_cluster:
            lines.append(f'    {node.id} {_node_attrs(node)};')

    lines.append("")
    for edge in spec.edges:
        lines.append(f'    {edge.src} -> {edge.dst} {_edge_attrs(edge)};')

    lines.append("}")
    return "\n".join(lines) + "\n"


def _emit_legend_dot(spec: PictureSpec, entries: dict[str, DictEntry]) -> str:
    """Emit DOT for the legend panel as a standalone graph.

    Reuses ``_emit_legend`` to keep the legend's HTML-table layout identical
    to the inline path; the wrapping digraph just gives graphviz something
    to render the panel inside of.
    """
    legend_block = _emit_legend(spec, entries, indent="    ")
    lines: list[str] = []
    lines.append("digraph legend {")
    lines.append('    bgcolor = "white";')
    lines.append(f'    fontname = "{FONT}";')
    lines.append('    dpi = 160;')
    lines.append(f'    node [fontname="{FONT}"];')
    lines.extend(legend_block)
    lines.append("}")
    return "\n".join(lines) + "\n"


def _emit_dot(spec: PictureSpec, entries: dict[str, DictEntry]) -> str:
    """Emit the full DOT source for a picture spec (inline-legend layout).

    Single-graph layout: figure + legend on one canvas with a 4:3 envelope.
    Kept as a fallback; ``render_composed`` is the default since v3.
    """
    lines: list[str] = []
    lines.append("digraph concept {")
    lines.append(f'    rankdir = {spec.rankdir};')
    lines.append('    bgcolor = "white";')
    lines.append(f'    fontname = "{FONT}";')
    lines.append('    fontsize = 28;')
    lines.append('    labelloc = "t";')
    # 4:3 canvas envelope — see SKILL.md "Canvas aspect ratio". 9.6 x 7.2 in
    # at 160 DPI gives a 1536 x 1152 PNG (4:3). We enforce the envelope by:
    #   - ``size="9.6,7.2!"`` clamps the page bounding box to 4:3,
    #   - ``ratio=0.75`` (height/width = 3/4) tells graphviz the target
    #     aspect ratio: it PADS the layout with whitespace to hit 4:3
    #     rather than stretching glyph positions (which ``ratio=fill``
    #     would do — that distorts the legend).
    # Combined, the output PNG is always 4:3; wide-natural layouts grow
    # whitespace top/bottom, tall-natural layouts grow whitespace left/right.
    lines.append('    size = "9.6,7.2!";')
    lines.append('    ratio = "0.75";')
    # newrank lets rank="sink" interact correctly with clusters.
    lines.append('    newrank = true;')
    if spec.title:
        lines.append(f'    label = "{_escape_dot_label(spec.title)}";')
    lines.append('    nodesep = 0.3;')
    lines.append('    ranksep = 0.45;')
    lines.append(
        f'    node [fontname="{FONT}", fontsize=24, style="filled", penwidth=1.0];'
    )
    lines.append(
        f'    edge [fontname="{FONT}", fontsize=20, color="#444444", penwidth=1.0];'
    )
    lines.append("")

    in_cluster: set[str] = set()
    for cluster in spec.clusters:
        in_cluster.update(cluster.contains)

    def emit_node(node: SpecNode, indent: str) -> str:
        return f'{indent}{node.id} {_node_attrs(node)};'

    for i, cluster in enumerate(spec.clusters):
        lines.append(f'    subgraph cluster_{i} {{')
        lines.append('        style = "dashed";')
        lines.append('        color = "#888";')
        lines.append(f'        label = "{_escape_dot_label(cluster.label)}";')
        for node in spec.nodes:
            if node.id in cluster.contains:
                lines.append(emit_node(node, "        "))
        lines.append('    }')

    for node in spec.nodes:
        if node.id not in in_cluster:
            lines.append(emit_node(node, "    "))

    lines.append("")
    for edge in spec.edges:
        lines.append(f'    {edge.src} -> {edge.dst} {_edge_attrs(edge)};')

    lines.append("")
    legend_lines = _emit_legend(spec, entries)
    lines.extend(legend_lines)

    # Anchor the legend to the right of the main graph. Without an edge
    # touching legend_panel, graphviz is free to place it anywhere and
    # rank="sink" alone won't pull it rightward across the cluster boundary.
    # We pick the last main-graph node as the anchor source; the edge is
    # styled invisible so it doesn't appear in the picture.
    if legend_lines and spec.nodes:
        anchor_src = spec.nodes[-1].id
        lines.append("")
        lines.append(
            f'    {anchor_src} -> legend_panel '
            '[style="invis", constraint=true];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Validation — report dict_id references that the dictionary doesn't cover.
# ---------------------------------------------------------------------------


def _validate(spec: PictureSpec, entries: dict[str, DictEntry]) -> list[str]:
    """Return a list of human-readable warnings for the spec."""
    warnings: list[str] = []

    node_ids = {n.id for n in spec.nodes}
    for n in spec.nodes:
        if n.dict_id not in entries:
            warnings.append(
                f"node {n.id!r}: unknown dict_id {n.dict_id!r} (not in DICTIONARY.md)"
            )
    for e in spec.edges:
        if e.src not in node_ids:
            warnings.append(f"edge: src {e.src!r} is not a declared node id")
        if e.dst not in node_ids:
            warnings.append(f"edge: dst {e.dst!r} is not a declared node id")
        if e.dict_id and e.dict_id not in entries:
            warnings.append(
                f"edge {e.src}->{e.dst}: unknown dict_id {e.dict_id!r} "
                "(not in DICTIONARY.md)"
            )
    return warnings


# ---------------------------------------------------------------------------
# Render entry point.
# ---------------------------------------------------------------------------


def _run_dot(dot_src: str, out_png: Path, *, emit_svg: bool) -> None:
    """Write ``dot_src`` to a sibling ``.dot`` and rasterize it.

    Also emits ``.svg`` when ``emit_svg`` is true. The ``.dot`` and the
    output share a stem so it's easy to inspect or hand-tune.
    """
    dot_path = out_png.with_suffix(".dot")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    dot_path.write_text(dot_src, encoding="utf-8")
    dot_exe = str(graphviz_dot())
    subprocess.run(
        [dot_exe, "-Tpng", str(dot_path), "-o", str(out_png)], check=True
    )
    print(f"wrote {dot_path}")
    print(f"wrote {out_png}")
    if emit_svg:
        svg_path = out_png.with_suffix(".svg")
        subprocess.run(
            [dot_exe, "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True
        )
        print(f"wrote {svg_path}")


def _compose_horizontal(
    left: Path, right: Path, out: Path, *, gutter: int = 60
) -> None:
    """Paste two PNGs side by side on a white canvas, vertically centered."""
    from PIL import Image

    a = Image.open(left).convert("RGBA")
    b = Image.open(right).convert("RGBA")
    h = max(a.height, b.height)
    w = a.width + gutter + b.width
    canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    canvas.paste(a, (0, (h - a.height) // 2), a)
    canvas.paste(b, (a.width + gutter, (h - b.height) // 2), b)
    canvas.convert("RGB").save(out)
    print(
        f"wrote {out}  size={canvas.size}  "
        f"ratio={canvas.size[0] / canvas.size[1]:.2f}"
    )


def render_inline(
    spec_path: Path, out_path: Path, *, emit_svg: bool = True
) -> None:
    """Single-graph render (figure + inline legend on one canvas, 4:3)."""
    entries = _load_dictionary()
    spec = _load_spec(spec_path)
    for w in _validate(spec, entries):
        print(f"WARNING: {w}", file=sys.stderr)
    _run_dot(_emit_dot(spec, entries), out_path, emit_svg=emit_svg)


def render_composed(
    spec_path: Path, out_path: Path, *, emit_svg: bool = True
) -> None:
    """Composed render — figure (TB) PNG + side-legend PNG, joined via PIL.

    This is the default since renderer v3 (variant 8). Forces the figure to
    use a top-to-bottom layout because graphviz ``dot`` only honors
    ``rankdir`` at the top level — letting the spec choose LR inside a
    cluster does nothing, and TB has consistently produced the best
    figure-vs-legend balance in evaluation.

    Intermediate figure/legend PNGs (and their .dot/.svg byproducts) are
    written to a tempdir and discarded on success; only the composed
    ``out_path`` remains on disk. ``emit_svg`` is ignored in this mode —
    composed mode is a raster pipeline (PIL paste) and a meaningful SVG
    would require a separate vector-compose step.
    """
    del emit_svg
    entries = _load_dictionary()
    spec = _load_spec(spec_path)
    for w in _validate(spec, entries):
        print(f"WARNING: {w}", file=sys.stderr)
    spec.rankdir = "TB"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="visualize_concept_") as td:
        fig_png = Path(td) / "figure.png"
        leg_png = Path(td) / "legend.png"
        _run_dot(_emit_figure_dot(spec, entries), fig_png, emit_svg=False)
        _run_dot(_emit_legend_dot(spec, entries), leg_png, emit_svg=False)
        _compose_horizontal(fig_png, leg_png, out_path)


def render(
    spec_path: Path,
    out_path: Path,
    *,
    emit_svg: bool = True,
    legend: str = "side",
) -> None:
    """Render the picture-spec at ``spec_path`` to ``out_path`` (PNG).

    Parameters
    ----------
    legend : {"side", "inline", "none"}
        ``"side"`` (default) uses ``render_composed`` — figure on the left,
        legend on the right, joined via PIL. ``"inline"`` falls back to the
        single-graph 4:3 layout. ``"none"`` renders the figure only.
    """
    if legend == "side":
        render_composed(spec_path, out_path, emit_svg=emit_svg)
    elif legend == "inline":
        render_inline(spec_path, out_path, emit_svg=emit_svg)
    elif legend == "none":
        entries = _load_dictionary()
        spec = _load_spec(spec_path)
        for w in _validate(spec, entries):
            print(f"WARNING: {w}", file=sys.stderr)
        spec.rankdir = "TB"
        _run_dot(_emit_figure_dot(spec, entries), out_path, emit_svg=emit_svg)
    else:
        raise ValueError(
            f"unknown --legend mode {legend!r}; expected side|inline|none"
        )


def _resolve_output_path(cli_out: Path | None, spec_path: Path) -> Path:
    """Resolve the output PNG path from CLI + spec.

    Resolution order (first match wins):

    1. ``cli_out`` (the CLI positional ``out``) when provided.
    2. Spec top-level ``output:`` resolved against
       ``vault_path(spec.slug, "figures/<output>.png")`` when both
       ``output`` and ``slug`` are present.

    Bare names without an extension get ``.png`` appended; explicit
    extensions are honored verbatim.
    """
    if cli_out is not None:
        return cli_out
    spec = _load_spec(spec_path)
    if spec.output is None or spec.slug is None:
        raise SystemExit(
            "no output path given on the CLI, and the spec is missing one or "
            "both of `slug:` / `output:` — cannot resolve where to write the "
            "PNG. Either pass `out` on the CLI or add both keys to the spec."
        )
    name = spec.output
    if Path(name).suffix == "":
        name = f"{name}.png"
    return vault_path(spec.slug, f"figures/{name}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Render a concept-picture YAML spec via graphviz, "
                    "resolving glyphs from DICTIONARY.md.",
    )
    p.add_argument("spec", type=Path, help="path to the picture-spec YAML")
    p.add_argument(
        "out",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "path to the output PNG. Optional — when omitted, the renderer "
            "resolves it from the spec's top-level `slug:` and `output:` "
            "keys via `vault_path(slug, 'figures/<output>.png')`."
        ),
    )
    p.add_argument("--no-svg", action="store_true", help="skip SVG output")
    p.add_argument(
        "--legend",
        choices=("side", "inline", "none"),
        default="side",
        help=(
            "legend layout: 'side' (default, v3 composed mode), "
            "'inline' (legacy single-graph 4:3), or 'none' (figure only)"
        ),
    )
    args = p.parse_args()

    out_path = _resolve_output_path(args.out, args.spec)
    print(f"output -> {out_path}")
    render(args.spec, out_path, emit_svg=not args.no_svg, legend=args.legend)


if __name__ == "__main__":
    main()
