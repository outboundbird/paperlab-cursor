# 2026-06-05 — Roadmap cleanup: export visualizer, park prerequisite, annotate two-memory

Housekeeping session (Agent mode). No agent/skill logic changed — only
`ROADMAP.md` and `AGENTS.md` prose, to reflect decisions the user made
about scope.

## Decisions applied

1. **Visualizer + figure-verifier → exported to an independent project.**
   - Removed `tools.tikz` Planned unit entirely (it existed only to serve
     the visualizer's slide/concept decks — SVG portability for TikZ
     fences; motivation dissolved with the decks).
   - Removed the long "On hold → Visualizer + figure-verifier" subsection,
     the "Reconsider slide-deck structure" schema candidate, and the
     "Subagents (on hold)" visualizer line in "what's currently working."
   - Renamed the "On hold" section to "Exported to a separate project"
     with a single sentence pointing at `visualizer-todo.md`.
   - Kept the `visualizer` / `figure-verifier` **agent-table rows** but
     restyled them: ♻️ + ~~strikethrough~~, status "Exported to
     independent project (2026-06-05)", invocation "(Not in this project)".
   - `AGENTS.md`: the visualizer "on hold" note became the
     exported-project sentence. (Left the general TikZ-as-diagram-escalation
     line in the math-notation rule — that is an authoring convention for
     any agent's diagrams, not visualizer-project prose.)

2. **`prerequisite` → parked.** It was a Planned unit (§2) plus an
   agent-table row. Removed the Planned-§2 prose; the user asked not to
   add it to the table, but it was already there, so the existing row was
   relabeled **Parked (2026-06-05)** / "(Parked — do not invoke)".

3. **Two-memory critic loop → annotated, not removed.** Verified the
   claim "built along with the experiment suite." Finding: the
   **firewall / generator-discriminator pattern** shipped in three gates
   (`blueprint-check`, `reconstructed`-source hop-2-vs-spec audit, Stage-2
   `extraction-fidelity`), but the loop's distinctive **architecture** —
   a persistent standing complementary representation wired to the reindex
   graph as substrate — is **not** built (the gates re-derive ad hoc per
   invocation, not graph-backed). Added a "Partially realized (2026-06-04)"
   sub-bullet recording exactly that split; kept the entry as remaining,
   corpus-gated, unscheduled work.

## Renumbering

Planned units renumbered after removing `tools.tikz`: Experimenter suite
§3→§1, External-data §4→§2, `tools.reindex` §5→§3. Checked for stale
"§4/§5" cross-references — the remaining ones are "blueprint §4
invariants" (unrelated).

## Not done

No commit yet (awaiting user). No code or agent-behavior change.
