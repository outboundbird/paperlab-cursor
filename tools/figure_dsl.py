"""Figure DSL — typed operator trees for concept pictures.

This module defines a small grammar for *composing* a concept picture from
dictionary atoms, instead of placing shapes on a graphviz canvas. An
operator tree carries spatial intent ("juxtapose" means side-by-side
comparison; "decompose" means whole-to-parts) that the renderer enforces.

The grammar is deliberately tiny in Phase 1:

- ``Leaf(dict_id, label)`` — a dictionary atom (E*/R*/A*) with a paper-
  notation label. The atomic visual unit.
- ``Juxtapose(left, right, gutter=...)`` — two sub-pictures side by side.
  Used when the paper presents two views of the same idea, or compares
  a global picture to a local one.
- ``Decompose(whole, parts, brace=...)`` — a whole on one side, its parts
  on the other, connected by a brace. Used when the paper factorizes or
  splits an object.

YAML surface
------------

The same tree is authored as nested YAML, with ``op:`` selecting the
operator and remaining keys supplying its arguments::

    op: Juxtapose
    left:
      op: Leaf
      dict_id: E1
      label: "Z_X^(l-1)"
    right:
      op: Decompose
      whole:
        op: Leaf
        dict_id: E5
        label: "q(z_A, z_X | A, X)"
      parts:
        - op: Leaf
          dict_id: E5
          label: "q(z_A | A, X)"
        - op: Leaf
          dict_id: E5
          label: "q(z_X | z_A, A, X)"

Parsing produces a typed tree (``Juxtapose | Decompose | Leaf``) which the
renderer walks. Validation is structural: each operator declares which
arguments are required and whether they must be ``Leaf`` or any operator.

Why this exists
---------------

The graphviz pipeline forces every figure into a node/edge layout, which
collapses to flowchart-style output regardless of how many cast/headline
hints the agent receives. The DSL inverts that: the agent picks an
operator tree (small decision space, semantically meaningful), and the
renderer owns the spatial layout per operator (matplotlib axes, brace
patches, etc.). See ROADMAP "Figure DSL" for the design rationale.

Phase 1 ships three operators only. New operators (Inset, RingOf, Plate,
Callout, BeforeAfter, ...) are added one at a time, each motivated by a
real paper figure that needs it. Resist the urge to design all twelve
upfront — the operator vocabulary is meant to grow from concrete need,
not from speculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import yaml


# ---------------------------------------------------------------------------
# Operator tree.
# ---------------------------------------------------------------------------


@dataclass
class Leaf:
    """A dictionary atom rendered at its position in the tree.

    Parameters
    ----------
    dict_id : str
        Dictionary entry id (``E1``, ``E5``, ``R10``, ``A1``, ...). The
        renderer uses this to select the visual idiom (shape, palette,
        glyph). See ``.cursor/skills/ml-visualization/DICTIONARY.md``.
    label : str
        Paper-notation label drawn inside the atom. Unicode math only
        (``θ``, ``Z_X^(l-1)``, ``μ``); no ``$...$`` delimiters, no
        backslash commands, no numerical values.
    """

    dict_id: str
    label: str = ""


@dataclass
class Juxtapose:
    """Two sub-pictures placed side by side with a gutter between them.

    The operator carries comparison intent: the reader is meant to read
    ``left`` and ``right`` as two views of the same idea, not as a
    sequential dataflow. The renderer draws them in equal-height axes
    with a small label gap; no connecting arrow.

    Parameters
    ----------
    left, right : Node
        Any operator subtree (including a single ``Leaf``).
    title : str, optional
        Caption above the pair. Empty by default.
    gutter : float
        Horizontal gap as a fraction of total width. Default ``0.08``.
    """

    left: Node
    right: Node
    title: str = ""
    gutter: float = 0.08


@dataclass
class Decompose:
    """A whole on the left, its parts on the right, joined by a brace.

    The operator carries factorization intent: the reader is meant to
    read ``whole = part_1 ⋄ part_2 ⋄ ...`` where ``⋄`` is the
    composition the paper specifies (often chained conditionals, often
    a product). The renderer draws a curly brace from the whole's right
    edge spanning the parts' vertical extent.

    Parameters
    ----------
    whole : Node
        The object being decomposed.
    parts : list[Node]
        Two or more sub-pictures, stacked vertically on the right.
    title : str, optional
        Caption above the operator's bounding box.
    relation : str, optional
        Short label drawn on the brace (``factors as``, ``=``, ``→``).
        Default ``"="``.
    """

    whole: Node
    parts: list[Node] = field(default_factory=list)
    title: str = ""
    relation: str = "="


# The full operator tree type.
Node = Union[Leaf, Juxtapose, Decompose]


# ---------------------------------------------------------------------------
# YAML parsing.
# ---------------------------------------------------------------------------


_OPS = {"Leaf": Leaf, "Juxtapose": Juxtapose, "Decompose": Decompose}


def parse_node(raw: dict) -> Node:
    """Recursively parse a YAML dict into a typed operator tree.

    Raises
    ------
    ValueError
        If ``op`` is missing or unknown, or if required arguments are
        absent for the named operator.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"expected a mapping with 'op:', got {type(raw).__name__}")
    op = raw.get("op")
    if op is None:
        raise ValueError(f"node missing 'op' key: {raw}")
    if op not in _OPS:
        raise ValueError(
            f"unknown operator {op!r}. Phase 1 supports: {sorted(_OPS)}"
        )

    if op == "Leaf":
        if "dict_id" not in raw:
            raise ValueError(f"Leaf missing 'dict_id': {raw}")
        return Leaf(dict_id=raw["dict_id"], label=raw.get("label", ""))

    if op == "Juxtapose":
        for k in ("left", "right"):
            if k not in raw:
                raise ValueError(f"Juxtapose missing {k!r}: {raw}")
        return Juxtapose(
            left=parse_node(raw["left"]),
            right=parse_node(raw["right"]),
            title=raw.get("title", ""),
            gutter=float(raw.get("gutter", 0.08)),
        )

    if op == "Decompose":
        if "whole" not in raw:
            raise ValueError(f"Decompose missing 'whole': {raw}")
        parts_raw = raw.get("parts") or []
        if len(parts_raw) < 2:
            raise ValueError(
                f"Decompose needs >= 2 'parts' (got {len(parts_raw)}): {raw}"
            )
        return Decompose(
            whole=parse_node(raw["whole"]),
            parts=[parse_node(p) for p in parts_raw],
            title=raw.get("title", ""),
            relation=raw.get("relation", "="),
        )

    raise AssertionError("unreachable")


@dataclass
class FigureSpec:
    """Top-level figure spec: a tree plus optional output naming hints."""

    title: str = ""
    root: Node | None = None
    slug: str | None = None
    output: str | None = None


def load_spec(path: Path) -> FigureSpec:
    """Parse a figure-spec YAML file into a ``FigureSpec``."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if "root" not in raw:
        raise ValueError(f"{path}: top-level spec missing 'root:' key")
    return FigureSpec(
        title=raw.get("title", ""),
        root=parse_node(raw["root"]),
        slug=raw.get("slug"),
        output=raw.get("output"),
    )


# ---------------------------------------------------------------------------
# Utilities (used by the renderer).
# ---------------------------------------------------------------------------


def walk(node: Node):
    """Yield ``node`` and every descendant in pre-order."""
    yield node
    if isinstance(node, Juxtapose):
        yield from walk(node.left)
        yield from walk(node.right)
    elif isinstance(node, Decompose):
        yield from walk(node.whole)
        for p in node.parts:
            yield from walk(p)


def count_leaves(node: Node) -> int:
    """Count ``Leaf`` instances under ``node`` (including ``node`` itself)."""
    return sum(1 for n in walk(node) if isinstance(n, Leaf))
