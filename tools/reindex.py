"""Build a graph index over the PaperLab vault.

``reindex`` is a deterministic, read-only parser. It walks the vault, reads
each artifact's YAML front-matter and body ``[[wiki-links]]``, and emits a
queryable graph (``graph.json``) under :func:`tools.paths.vault_index_dir`.

The index is a **derived cache** — rebuilt from the markdown, never
hand-edited. If lost, rerun this tool.

Scope (v1)
----------
- Walks per-paper folders ``<vault>/<slug>/*.md`` and multi-paper
  ``<vault>/experiments/<topic>/*.md``.
- Parses front-matter keys: ``paper`` / ``topic`` + ``papers``, ``agent``,
  ``status``, ``sources``, ``concepts``. Also collects body ``[[wiki-links]]``.
- Emits nodes (papers, topics, artifacts, concepts) and edges
  (``derived_from``, ``mentions``, ``has_status``).
- Reports drift to stderr: unknown concept names (not in
  ``.cursor/skills/concept-vocabulary.md``), artifacts missing the schema
  keys, and ``sources`` links that don't resolve to a known artifact.

Out of scope (v1) — see ``ROADMAP.md`` §5:
- Source content-hash staleness (needs a write-side stamp).
- Concept auto-normalization (report only; never rename).
- A human-facing ``_index.md`` rollup (JSON only).

Examples
--------
>>> python -m tools.reindex            # build and write graph.json
>>> python -m tools.reindex --check    # report drift only, write nothing
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tools.paths import repo_root, vault_index_dir, vault_root


WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

CONCEPT_VOCAB_REL = Path(".cursor") / "skills" / "concept-vocabulary.md"
CONCEPT_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class GraphNode:
    """A node in the index graph.

    Parameters
    ----------
    id : str
        Stable identifier (e.g. ``paper:GIB``, ``artifact:GIB/spec.md``,
        ``concept:information-bottleneck``, ``topic:gib-comparison``).
    kind : str
        One of ``paper``, ``topic``, ``artifact``, ``concept``.
    attrs : dict
        Free-form attributes (agent, status, path, ...).
    """

    id: str
    kind: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A directed edge: ``src`` --rel--> ``dst``."""

    src: str
    rel: str
    dst: str


@dataclass
class Drift:
    """Collected drift warnings, reported to stderr but never fatal."""

    unknown_concepts: list[str] = field(default_factory=list)
    missing_schema: list[str] = field(default_factory=list)
    unresolved_sources: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.unknown_concepts or self.missing_schema or self.unresolved_sources
        )


def _normalize_wikilink(target: str) -> str:
    """Strip a ``[[link|alias]]`` to its target and trim whitespace.

    Obsidian allows ``[[path|display text]]``; we index by the path part only.
    """
    return target.split("|", 1)[0].strip()


def parse_front_matter(text: str) -> dict[str, Any]:
    """Extract the YAML front-matter block from a markdown string.

    Returns an empty dict if the file has no leading ``--- ... ---`` block or
    if the block fails to parse.
    """
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def load_concept_vocab() -> set[str]:
    """Load canonical concept names from ``concept-vocabulary.md``.

    Names are the ``### <canonical-name>`` headings under the "Concepts"
    section. Returns an empty set if the file is absent (grow-on-demand: the
    list may legitimately be empty early on).
    """
    vocab_path = repo_root() / CONCEPT_VOCAB_REL
    if not vocab_path.is_file():
        return set()
    text = vocab_path.read_text(encoding="utf-8")
    return {m.strip() for m in CONCEPT_HEADING_RE.findall(text)}


def _iter_markdown(vault: Path) -> list[Path]:
    """All ``.md`` files under the vault, excluding the ``.index/`` cache."""
    index_dir = vault_index_dir()
    out: list[Path] = []
    for path in sorted(vault.rglob("*.md")):
        if index_dir in path.parents:
            continue
        out.append(path)
    return out


def _as_list(value: Any) -> list[str]:
    """Coerce a front-matter value into a list of strings.

    Tolerates ``None`` (missing), a scalar, or a list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def build_graph(vault: Path) -> tuple[list[GraphNode], list[GraphEdge], Drift]:
    """Walk the vault and build nodes, edges, and a drift report.

    Parameters
    ----------
    vault : Path
        The PaperLab vault root.

    Returns
    -------
    tuple
        ``(nodes, edges, drift)``.
    """
    vocab = load_concept_vocab()
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    drift = Drift()
    artifact_ids: set[str] = set()

    def ensure(node_id: str, kind: str, **attrs: Any) -> None:
        if node_id not in nodes:
            nodes[node_id] = GraphNode(id=node_id, kind=kind, attrs=dict(attrs))
        else:
            nodes[node_id].attrs.update({k: v for k, v in attrs.items() if v is not None})

    for path in _iter_markdown(vault):
        rel = path.relative_to(vault).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_front_matter(text)

        artifact_id = f"artifact:{rel}"
        artifact_ids.add(artifact_id)

        agent = fm.get("agent")
        status = fm.get("status")
        ensure(artifact_id, "artifact", path=rel, agent=agent, status=status)

        # Paper or topic membership.
        if "paper" in fm and fm["paper"]:
            paper = str(fm["paper"])
            ensure(f"paper:{paper}", "paper", slug=paper)
            edges.append(GraphEdge(f"paper:{paper}", "has_artifact", artifact_id))
        if "topic" in fm and fm["topic"]:
            topic = str(fm["topic"])
            ensure(f"topic:{topic}", "topic", name=topic)
            edges.append(GraphEdge(f"topic:{topic}", "has_artifact", artifact_id))
            for paper in _as_list(fm.get("papers")):
                ensure(f"paper:{paper}", "paper", slug=paper)
                edges.append(GraphEdge(f"topic:{topic}", "includes_paper", f"paper:{paper}"))

        # Schema-completeness drift (skip the user-owned notes.md).
        if path.name != "notes.md":
            missing = [k for k in ("agent", "status") if not fm.get(k)]
            if missing:
                drift.missing_schema.append(f"{rel}: missing {', '.join(missing)}")

        # has_status edge.
        if status:
            ensure(f"status:{status}", "status", name=status)
            edges.append(GraphEdge(artifact_id, "has_status", f"status:{status}"))

        # derived_from edges (from `sources` front-matter wiki-links).
        for src in _as_list(fm.get("sources")):
            for link in WIKILINK_RE.findall(src) or [src]:
                target = _normalize_wikilink(link)
                dst = f"artifact:{target}"
                edges.append(GraphEdge(artifact_id, "derived_from", dst))

        # mentions edges (from `concepts` front-matter + body wiki-links).
        concept_links: set[str] = set()
        for c in _as_list(fm.get("concepts")):
            for link in WIKILINK_RE.findall(c) or [c]:
                concept_links.add(_normalize_wikilink(link))
        for link in WIKILINK_RE.findall(text):
            target = _normalize_wikilink(link)
            # Body links that look like artifacts (contain a slash) are
            # provenance-ish, not concepts; concept links are bare names.
            if "/" not in target and not target.endswith(".md"):
                concept_links.add(target)

        for concept in concept_links:
            if concept.startswith("<") or not concept:
                continue  # schema placeholder like <canonical-concept-name>
            ensure(f"concept:{concept}", "concept", name=concept)
            edges.append(GraphEdge(artifact_id, "mentions", f"concept:{concept}"))
            if vocab and concept not in vocab:
                drift.unknown_concepts.append(f"{rel}: '{concept}' not in vocabulary")

    # Resolve derived_from targets against known artifacts.
    for edge in edges:
        if edge.rel == "derived_from" and edge.dst not in artifact_ids:
            target = edge.dst.split(":", 1)[1]
            if not target.startswith("<"):  # skip schema placeholders
                drift.unresolved_sources.append(
                    f"{edge.src.split(':', 1)[1]}: source '{target}' not found"
                )

    return list(nodes.values()), edges, drift


def to_dict(nodes: list[GraphNode], edges: list[GraphEdge]) -> dict[str, Any]:
    """Serialize the graph into a JSON-ready dict."""
    return {
        "version": 1,
        "nodes": [{"id": n.id, "kind": n.kind, **n.attrs} for n in nodes],
        "edges": [{"src": e.src, "rel": e.rel, "dst": e.dst} for e in edges],
    }


def report_drift(drift: Drift) -> None:
    """Print drift warnings to stderr. Never fatal."""
    if drift.is_empty():
        print("reindex: no drift detected.", file=sys.stderr)
        return
    if drift.missing_schema:
        print("reindex: artifacts missing schema keys:", file=sys.stderr)
        for line in drift.missing_schema:
            print(f"  - {line}", file=sys.stderr)
    if drift.unknown_concepts:
        print("reindex: concept names not in vocabulary:", file=sys.stderr)
        for line in drift.unknown_concepts:
            print(f"  - {line}", file=sys.stderr)
    if drift.unresolved_sources:
        print("reindex: unresolved source links:", file=sys.stderr)
        for line in drift.unresolved_sources:
            print(f"  - {line}", file=sys.stderr)


def reindex(write: bool = True) -> dict[str, Any]:
    """Build the graph and optionally write ``graph.json``.

    Parameters
    ----------
    write : bool
        If ``True``, write ``graph.json`` to :func:`vault_index_dir`. If
        ``False`` (``--check`` mode), only report drift.

    Returns
    -------
    dict
        The serialized graph.
    """
    vault = vault_root()
    nodes, edges, drift = build_graph(vault)
    graph = to_dict(nodes, edges)

    if write:
        out_dir = vault_index_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "graph.json"
        out_path.write_text(
            json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(
            f"reindex: wrote {len(nodes)} nodes, {len(edges)} edges -> {out_path}",
            file=sys.stderr,
        )

    report_drift(drift)
    return graph


def _cli() -> None:
    """``python -m tools.reindex [--check]``."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(_cli.__doc__)
        return
    write = "--check" not in args
    reindex(write=write)


if __name__ == "__main__":
    _cli()
