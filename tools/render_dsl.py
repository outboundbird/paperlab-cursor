"""Figure DSL renderer — matplotlib backend.

Walks an operator tree (see ``tools.figure_dsl``) and rasterises it to
PNG. Each operator owns its own layout function:

- ``Leaf``      → draws the dictionary atom's shape with the paper-
                  notation label inside.
- ``Juxtapose`` → two equal-height bounding boxes side by side with a
                  gutter and an optional title.
- ``Decompose`` → ``whole`` on the left, ``parts`` stacked on the right,
                  joined by a curly brace carrying ``relation``.

Layout strategy
---------------

Two-pass, bottom-up:

1. **Measure.** Every node returns its natural ``(width, height)`` in
   *figure units* (one unit ≈ one rendered inch at 100 DPI). Leaves
   measure their label and pick a minimum chip size; composites add
   gutter/brace/title costs.
2. **Place.** Walk top-down, handing each child a target ``(x, y, w, h)``
   box and asking it to draw inside.

This keeps each operator's layout local — adding a new operator
(``Inset``, ``RingOf``, ``Plate``, ...) means writing one ``measure_*``
and one ``place_*`` function without touching the others.

Palette mirrors ``tools.visualize_concept._NODE_STYLE`` so leaves render
in the same visual language as the legacy graphviz path while we ship
the DSL.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Bbox

from tools.figure_dsl import (
    Decompose,
    FigureSpec,
    Juxtapose,
    Leaf,
    Node,
    load_spec,
)


# ---------------------------------------------------------------------------
# Per-``dict_id`` leaf style. Each entry is a triple ``(shape_kind, fill,
# stroke)`` mirroring the graphviz palette in ``visualize_concept._NODE_STYLE``
# so the DSL and the legacy path stay visually consistent for the moment.
#
# ``shape_kind`` is one of:
#   - ``"chip"``      rounded rectangle (E1, E3, E11, E14, E16, E19, E20)
#   - ``"ellipse"``   axis-aligned ellipse  (E4, E5, E15, E21)
#   - ``"disc"``      small filled circle   (E2, E10, E13, E18)
#   - ``"dashed_box"`` dashed-border rect   (E7)
#   - ``"trapezium"`` symmetric trapezium   (E22)
#   - ``"cylinder"``  squat cylinder        (E8)
#   - ``"folder"``    notched chip          (E9)
#   - ``"octagon"``   stop-sign octagon     (E23)
# ---------------------------------------------------------------------------

_LEAF_STYLE: dict[str, tuple[str, str, str]] = {
    "E1": ("chip", "#cfe2ff", "#0d6efd"),
    "E2": ("disc", "#fff3cd", "#a07a00"),
    "E3": ("chip", "#cfe2ff", "#0d6efd"),
    "E4": ("ellipse", "#f8d7da", "#a23b3b"),
    "E5": ("ellipse", "#f8d7da", "#a23b3b"),
    "E6": ("chip", "#ffe9b3", "#a64b00"),
    "E7": ("dashed_box", "#e9ecef", "#495057"),
    "E8": ("cylinder", "#e9ecef", "#495057"),
    "E9": ("folder", "#e9ecef", "#495057"),
    "E10": ("disc", "#cfe2ff", "#0d6efd"),
    "E11": ("chip", "#cfe2ff", "#0d6efd"),
    "E13": ("disc", "#d1e7dd", "#1c5e3c"),
    "E14": ("chip", "#d1e7dd", "#1c5e3c"),
    "E15": ("ellipse", "#d1e7dd", "#1c5e3c"),
    "E16": ("chip", "#cfe2ff", "#0d6efd"),
    "E18": ("disc", "#f5d6f5", "#7a3a7a"),
    "E19": ("chip", "#e9ecef", "#495057"),
    "E20": ("chip", "#cfe2ff", "#0d6efd"),
    "E21": ("ellipse", "#f0f0f0", "#888888"),
    "E22": ("trapezium", "#fff3cd", "#a07a00"),
    "E23": ("octagon", "#f8d7da", "#a23b3b"),
}
_FALLBACK_LEAF = ("chip", "#cfe2ff", "#0d6efd")


# Layout constants. Figure units are inches at 100 DPI; tuned by hand on the
# Phase 1 reference YAML and likely to evolve as the operator set grows.
LEAF_MIN_W = 2.4
LEAF_MIN_H = 1.0
LEAF_PAD_X = 0.3
LEAF_PAD_Y = 0.15
LABEL_FONTSIZE = 18
TITLE_FONTSIZE = 22
BRACE_FONTSIZE = 16
DECOMPOSE_PART_GAP = 0.4
DECOMPOSE_BRACE_WIDTH = 1.3
DECOMPOSE_CONNECTOR_GAP = 0.9  # horizontal clearance between whole and brace tip
JUXTAPOSE_TITLE_H = 0.6
JUXTAPOSE_PANEL_PAD = 0.08
DECOMPOSE_TITLE_H = 0.5


# ---------------------------------------------------------------------------
# Measure pass: each node reports its natural (width, height).
# ---------------------------------------------------------------------------


@dataclass
class Size:
    w: float
    h: float


def _measure_leaf_label(label: str) -> Size:
    """Approximate label box from character count and line count.

    Matplotlib doesn't expose font metrics until a figure exists, and
    creating one per-measure is expensive. A character-count estimate
    (0.13 in per char at 18pt, 0.32 in per line) is good enough for
    Phase 1; if a label overflows its chip the renderer will draw it
    but the chip won't auto-grow. Tune ``LEAF_MIN_*`` if this becomes a
    problem.
    """
    lines = label.split("\n") if label else [""]
    max_chars = max((len(l) for l in lines), default=0)
    w = max(LEAF_MIN_W, 0.13 * max_chars + 2 * LEAF_PAD_X)
    h = max(LEAF_MIN_H, 0.32 * len(lines) + 2 * LEAF_PAD_Y)
    return Size(w, h)


def measure(node: Node) -> Size:
    """Return the natural size of ``node`` in figure units."""
    if isinstance(node, Leaf):
        return _measure_leaf_label(node.label)

    if isinstance(node, Juxtapose):
        ls = measure(node.left)
        rs = measure(node.right)
        gutter = node.gutter * (ls.w + rs.w)
        title_h = JUXTAPOSE_TITLE_H if node.title else 0.0
        return Size(ls.w + gutter + rs.w, max(ls.h, rs.h) + title_h)

    if isinstance(node, Decompose):
        ws = measure(node.whole)
        part_sizes = [measure(p) for p in node.parts]
        parts_w = max((p.w for p in part_sizes), default=0.0)
        parts_h = sum(p.h for p in part_sizes) + DECOMPOSE_PART_GAP * (
            len(part_sizes) - 1
        )
        title_h = DECOMPOSE_TITLE_H if node.title else 0.0
        return Size(
            ws.w + DECOMPOSE_CONNECTOR_GAP + DECOMPOSE_BRACE_WIDTH + parts_w,
            max(ws.h, parts_h) + title_h,
        )

    raise TypeError(f"unknown node type: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Place pass: draw ``node`` inside the given (x, y, w, h) on the axes.
# ---------------------------------------------------------------------------


def _draw_leaf(ax, node: Leaf, x: float, y: float, w: float, h: float) -> None:
    """Render a leaf inside its allotted box, centered."""
    kind, fill, stroke = _LEAF_STYLE.get(node.dict_id, _FALLBACK_LEAF)
    cx, cy = x + w / 2, y + h / 2

    if kind == "chip":
        patch = mpatches.FancyBboxPatch(
            (x + LEAF_PAD_X, y + LEAF_PAD_Y),
            w - 2 * LEAF_PAD_X, h - 2 * LEAF_PAD_Y,
            boxstyle="round,pad=0.05,rounding_size=0.15",
            linewidth=1.8, edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(patch)
    elif kind == "ellipse":
        patch = mpatches.Ellipse(
            (cx, cy), w - 2 * LEAF_PAD_X, h - 2 * LEAF_PAD_Y,
            linewidth=2.0, edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(patch)
    elif kind == "disc":
        r = min(w, h) / 2 - LEAF_PAD_Y
        patch = mpatches.Circle(
            (cx, cy), r, linewidth=1.8, edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(patch)
    elif kind == "dashed_box":
        patch = mpatches.FancyBboxPatch(
            (x + LEAF_PAD_X, y + LEAF_PAD_Y),
            w - 2 * LEAF_PAD_X, h - 2 * LEAF_PAD_Y,
            boxstyle="round,pad=0.05,rounding_size=0.05",
            linewidth=1.6, edgecolor=stroke, facecolor=fill,
            linestyle="--",
        )
        ax.add_patch(patch)
    elif kind == "trapezium":
        # symmetric trapezium, narrower on top
        inset = (w - 2 * LEAF_PAD_X) * 0.18
        verts = [
            (x + LEAF_PAD_X + inset, y + h - LEAF_PAD_Y),
            (x + w - LEAF_PAD_X - inset, y + h - LEAF_PAD_Y),
            (x + w - LEAF_PAD_X, y + LEAF_PAD_Y),
            (x + LEAF_PAD_X, y + LEAF_PAD_Y),
        ]
        patch = mpatches.Polygon(
            verts, closed=True, linewidth=1.8,
            edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(patch)
    elif kind == "cylinder":
        body = mpatches.FancyBboxPatch(
            (x + LEAF_PAD_X, y + LEAF_PAD_Y + 0.1),
            w - 2 * LEAF_PAD_X, h - 2 * LEAF_PAD_Y - 0.2,
            boxstyle="round,pad=0.0,rounding_size=0.0",
            linewidth=1.6, edgecolor=stroke, facecolor=fill,
        )
        cap_top = mpatches.Ellipse(
            (cx, y + h - LEAF_PAD_Y - 0.1),
            w - 2 * LEAF_PAD_X, 0.2,
            linewidth=1.6, edgecolor=stroke, facecolor=fill,
        )
        cap_bot = mpatches.Ellipse(
            (cx, y + LEAF_PAD_Y + 0.1),
            w - 2 * LEAF_PAD_X, 0.2,
            linewidth=1.6, edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(body)
        ax.add_patch(cap_bot)
        ax.add_patch(cap_top)
    elif kind == "folder":
        tab_h = 0.18
        body = mpatches.FancyBboxPatch(
            (x + LEAF_PAD_X, y + LEAF_PAD_Y),
            w - 2 * LEAF_PAD_X, h - 2 * LEAF_PAD_Y - tab_h,
            boxstyle="round,pad=0.0,rounding_size=0.08",
            linewidth=1.6, edgecolor=stroke, facecolor=fill,
        )
        tab = mpatches.FancyBboxPatch(
            (x + LEAF_PAD_X, y + h - LEAF_PAD_Y - tab_h),
            (w - 2 * LEAF_PAD_X) * 0.4, tab_h,
            boxstyle="round,pad=0.0,rounding_size=0.06",
            linewidth=1.6, edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(body)
        ax.add_patch(tab)
    elif kind == "octagon":
        cut = min(w, h) * 0.18
        verts = [
            (x + LEAF_PAD_X + cut, y + LEAF_PAD_Y),
            (x + w - LEAF_PAD_X - cut, y + LEAF_PAD_Y),
            (x + w - LEAF_PAD_X, y + LEAF_PAD_Y + cut),
            (x + w - LEAF_PAD_X, y + h - LEAF_PAD_Y - cut),
            (x + w - LEAF_PAD_X - cut, y + h - LEAF_PAD_Y),
            (x + LEAF_PAD_X + cut, y + h - LEAF_PAD_Y),
            (x + LEAF_PAD_X, y + h - LEAF_PAD_Y - cut),
            (x + LEAF_PAD_X, y + LEAF_PAD_Y + cut),
        ]
        patch = mpatches.Polygon(
            verts, closed=True, linewidth=1.8,
            edgecolor=stroke, facecolor=fill,
        )
        ax.add_patch(patch)
    else:
        # defensive fallback
        ax.add_patch(mpatches.Rectangle(
            (x, y), w, h, linewidth=1.5, edgecolor="black", facecolor="white"
        ))

    if node.label:
        ax.text(
            cx, cy, node.label, ha="center", va="center",
            fontsize=LABEL_FONTSIZE, color="#222",
        )


def _draw_brace(ax, x: float, y0: float, y1: float, w: float, label: str) -> Tuple[float, float]:
    """Draw a left-facing curly brace ``{`` spanning ``y0..y1``.

    Returns the (x, y) of the brace's tip — used by the caller to draw a
    connector from the whole to the tip.

    Geometry:
      - vertical body runs along the parts-side edge of the brace's
        allotted width (``x + w * 0.85``); this is where the brace hugs
        the parts column.
      - tip is a single inward point at the vertical center, pulled
        toward the whole (``x + w * 0.05``).
      - top and bottom hooks curve inward to the body line, then the
        body line travels down to the matching hook on the other end.

    All four corners use small quadratic-Bezier hooks so the brace reads
    as a smooth ``{`` rather than two straight lines meeting at a tip.
    """
    body_x = x + w * 0.85
    tip_x = x + w * 0.05
    yc = (y0 + y1) / 2
    hook = min(0.25, (y1 - y0) * 0.12)

    # Path traces:
    #   top-end (body_x, y1)
    #   → quadratic curve to top of body line (body_x, y1 - hook)
    #   → straight down to top-tip hook start (body_x, yc + hook)
    #   → quadratic curve to tip (tip_x, yc)
    #   → quadratic curve back to bottom of body line (body_x, yc - hook)
    #   → straight down to bottom-end hook (body_x, y0 + hook)
    #   → quadratic curve to bottom-end (body_x, y0)
    verts = [
        (body_x, y1),
        (body_x - hook * 0.5, y1),       # ctrl: pull the end slightly inward
        (body_x, y1 - hook),             # endpoint of top hook
        (body_x, yc + hook),             # straight body
        (body_x, yc + hook * 0.5),       # ctrl
        (tip_x, yc),                     # tip
        (body_x, yc - hook * 0.5),       # ctrl
        (body_x, yc - hook),             # back on body
        (body_x, y0 + hook),             # straight body
        (body_x - hook * 0.5, y0),       # ctrl
        (body_x, y0),                    # end
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE3, MplPath.CURVE3,  # top hook
        MplPath.LINETO,                  # body
        MplPath.CURVE3, MplPath.CURVE3,  # to tip
        MplPath.CURVE3, MplPath.CURVE3,  # from tip
        MplPath.LINETO,                  # body
        MplPath.CURVE3, MplPath.CURVE3,  # bottom hook
    ]
    path = MplPath(verts, codes)
    ax.add_patch(mpatches.PathPatch(
        path, facecolor="none", edgecolor="#444", linewidth=2.2,
    ))
    # Label is drawn by the caller (Decompose.place) so it can sit on the
    # connector at a known x range rather than crowding the brace tip.
    _ = label
    return (tip_x, yc)


def place(ax, node: Node, x: float, y: float, w: float, h: float) -> None:
    """Draw ``node`` inside the (x, y, w, h) box on ``ax``."""
    if isinstance(node, Leaf):
        _draw_leaf(ax, node, x, y, w, h)
        return

    if isinstance(node, Juxtapose):
        title_h = JUXTAPOSE_TITLE_H if node.title else 0.0
        if node.title:
            ax.text(
                x + w / 2, y + h - title_h / 2, node.title,
                ha="center", va="center",
                fontsize=TITLE_FONTSIZE, color="#222", fontweight="bold",
            )
        body_h = h - title_h
        ls = measure(node.left)
        rs = measure(node.right)
        gutter = node.gutter * (ls.w + rs.w)
        total = ls.w + gutter + rs.w
        scale = w / total
        lw = ls.w * scale
        rw = rs.w * scale
        gx = gutter * scale
        # Per-side background panels carry "two views" intent: each half
        # sits on its own pale-grey rounded panel so the reader sees one
        # composition, not two disconnected pictures.
        pad = JUXTAPOSE_PANEL_PAD
        for px, pw in ((x, lw), (x + lw + gx, rw)):
            panel = mpatches.FancyBboxPatch(
                (px + pad, y + pad),
                pw - 2 * pad, body_h - 2 * pad,
                boxstyle="round,pad=0.05,rounding_size=0.20",
                linewidth=1.2, edgecolor="#bbb", facecolor="#fafafa",
                zorder=0,
            )
            ax.add_patch(panel)
        place(ax, node.left,  x,             y, lw, body_h)
        place(ax, node.right, x + lw + gx,   y, rw, body_h)
        return

    if isinstance(node, Decompose):
        title_h = DECOMPOSE_TITLE_H if node.title else 0.0
        if node.title:
            ax.text(
                x + w / 2, y + h - title_h / 2, node.title,
                ha="center", va="center",
                fontsize=TITLE_FONTSIZE, color="#222", fontweight="bold",
            )
        body_h = h - title_h

        ws = measure(node.whole)
        part_sizes = [measure(p) for p in node.parts]
        parts_w_natural = max((p.w for p in part_sizes), default=0.0)
        natural_total = (
            ws.w + DECOMPOSE_CONNECTOR_GAP + DECOMPOSE_BRACE_WIDTH + parts_w_natural
        )
        scale_x = w / natural_total
        whole_w = ws.w * scale_x
        connector_w = DECOMPOSE_CONNECTOR_GAP * scale_x
        brace_w = DECOMPOSE_BRACE_WIDTH * scale_x
        parts_w = parts_w_natural * scale_x

        # Whole on the left, vertically centered in body_h.
        whole_h = min(ws.h, body_h * 0.9)
        whole_y = y + (body_h - whole_h) / 2
        place(ax, node.whole, x, whole_y, whole_w, whole_h)

        # Parts stacked on the right.
        n_parts = len(part_sizes)
        gaps_total = DECOMPOSE_PART_GAP * (n_parts - 1)
        natural_parts_h = sum(p.h for p in part_sizes) + gaps_total
        scale_y = min(1.0, (body_h * 0.95) / natural_parts_h) if natural_parts_h > 0 else 1.0
        scaled_part_hs = [p.h * scale_y for p in part_sizes]
        scaled_gap = DECOMPOSE_PART_GAP * scale_y
        total_parts_h = sum(scaled_part_hs) + scaled_gap * (n_parts - 1)
        parts_start_y = y + (body_h - total_parts_h) / 2
        parts_x = x + whole_w + connector_w + brace_w
        # Place parts top→bottom: YAML order matches reading order.
        cy = parts_start_y + total_parts_h
        for p, ph in zip(node.parts, scaled_part_hs):
            cy -= ph
            place(ax, p, parts_x, cy, parts_w, ph)
            cy -= scaled_gap

        # Brace spans the parts' vertical extent and points its tip back
        # toward the whole. The brace sits in the brace_w column that
        # starts AFTER the connector gap.
        brace_x = x + whole_w + connector_w
        tip_xy = _draw_brace(
            ax,
            x=brace_x,
            y0=parts_start_y,
            y1=parts_start_y + total_parts_h,
            w=brace_w,
            label=node.relation,
        )
        # Connector: horizontal line from the whole's right edge to the
        # brace tip. Sits inside the connector_w gap so there's room
        # above it for the relation label.
        whole_right_x = x + whole_w - LEAF_PAD_X
        whole_cy = whole_y + whole_h / 2
        ax.plot(
            [whole_right_x, tip_xy[0]],
            [whole_cy, tip_xy[1]],
            color="#444", linewidth=1.6, solid_capstyle="round",
        )
        # Relation label sits above the connector midpoint, italic.
        if node.relation:
            mid_x = (whole_right_x + tip_xy[0]) / 2
            mid_y = (whole_cy + tip_xy[1]) / 2
            ax.text(
                mid_x, mid_y + 0.25, node.relation,
                ha="center", va="bottom",
                fontsize=BRACE_FONTSIZE, color="#444", style="italic",
            )
        return

    raise TypeError(f"unknown node type: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Top-level entry.
# ---------------------------------------------------------------------------


def render(spec: FigureSpec, out_png: Path, *, dpi: int = 150) -> None:
    """Rasterise ``spec`` to ``out_png``."""
    if spec.root is None:
        raise ValueError("FigureSpec has no root operator")

    root_size = measure(spec.root)

    # Top-level title sits above the root tree.
    top_title_h = 0.7 if spec.title else 0.0
    margin = 0.5
    # Reserve enough width so the title doesn't overflow the canvas. The
    # 0.16-in/char estimate is conservative for TITLE_FONTSIZE bold.
    title_w_needed = 0.16 * len(spec.title) + 2 * margin if spec.title else 0
    fig_w = max(root_size.w + 2 * margin, title_w_needed)
    fig_h = root_size.h + top_title_h + 2 * margin

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.set_aspect("equal")
    ax.axis("off")

    if spec.title:
        ax.text(
            fig_w / 2, fig_h - margin - top_title_h / 2,
            spec.title,
            ha="center", va="center",
            fontsize=TITLE_FONTSIZE, color="#111",
            fontweight="bold",
            wrap=True,
        )

    root_x = (fig_w - root_size.w) / 2
    place(ax, spec.root,
          x=root_x, y=margin,
          w=root_size.w, h=root_size.h)

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches=Bbox([[0, 0], [fig_w, fig_h]]))
    plt.close(fig)
    print(f"wrote {out_png}  size=({int(fig_w*dpi)}, {int(fig_h*dpi)})")


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Render a figure-DSL YAML to PNG.")
    p.add_argument("spec", type=Path, help="path to the DSL YAML spec")
    p.add_argument(
        "out", type=Path, nargs="?",
        help="output PNG path (overrides spec slug/output if given)",
    )
    p.add_argument("--dpi", type=int, default=150)
    args = p.parse_args()

    spec = load_spec(args.spec)

    if args.out is not None:
        out_path = args.out
    elif spec.slug and spec.output:
        from tools.paths import vault_path
        out_path = vault_path(
            spec.slug, f"figures/{spec.output}.png"
        )
    else:
        out_path = args.spec.with_suffix(".png")

    render(spec, out_path, dpi=args.dpi)


if __name__ == "__main__":
    main()
