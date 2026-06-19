# paperlab

`paperlab` is a multiagent system to help students understand papers in machine learning and deep learning.

## Quick start

Copy `paperlab.config.example.yaml` to `paperlab.config.yaml` and set `repo_root` and `vault_paperlab_path`. Resolve paths with [`tools/paths.py`](./tools/paths.py) (`python -m tools.paths …`).

| You want to… | Start here |
| --- | --- |
| Add a paper (PDF, supplements, optional upstream clone) | `acquirer` — e.g. acquire `<slug>` with a paper URL |
| Get a structured `spec.md` from the PDF | `dissector` (often auto-chained after acquire) |
| Map the paper to code or a blueprint | `implementer` |
| Audit claims and code alignment | `critic` |
| Talk through concepts with a tutor | `/tutor <slug>` |
| Compare methods across papers on one topic | `comparator` or `/experimenter <topic>` |
| Turn a blueprint into runnable per-paper code | `/coder code <slug>` |

**Status.** Learning suite and Experimenter suite (including `coder` Stage 2 and `evaluator`) are shipped; open follow-ups live in [`ROADMAP.md`](./ROADMAP.md).

## Documentation map

- [`AGENTS.md`](./AGENTS.md) — **authoritative** reference for subagents and skills (roles, YAML, verifier system, paths, sandbox).
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — human-oriented orchestration overview (diagrams, design principles); **not** normative for agent behavior.
- [`ROADMAP.md`](./ROADMAP.md) — what is shipped, what is next, known limitations.
- [`log/`](./log/) — dated design and validation narratives.
