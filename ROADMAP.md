# PaperLab Roadmap

Status as of YYYY-MM-DD. This is a living document — items move between sections as their status changes.

## Deferred features

Things explicitly deferred during design, with the reason. Each entry
should be specific enough to act on without rereading the whole
conversation that produced it.

### [Feature name]

- **What:** one-sentence description
- **Why deferred:** the actual reason (not "out of scope" — be specific)
- **Trigger to revisit:** what condition would make this worth building
- **Estimated effort:** rough sense of size (small / medium / large)
- **Notes:** any design decisions already made

## Known limitations

Things the system can't do, with workarounds where they exist. Distinct
from deferred features — these are constraints, not unbuilt work.

### [Limitation name]

- **What:** what doesn't work
- **Why:** root cause (architectural, environmental, etc.)
- **Workaround:** what you do instead
- **Possible fix:** if any, with rough effort

## Schema improvement candidates

Small refinements to existing schemas that aren't urgent but are worth
remembering. These tend to surface during use.

- **[Schema/section]:** what to change, why

## Migration notes

Things to keep in mind when migrating to Cursor (Option C).

- **What ports cleanly:** schemas, artifacts, conventions
- **What needs rewriting:** agent files (`.claude/agents/*.md`)
- **What needs new design:** anything that depends on Claude Code's
  subagent-with-fresh-context model

## Reference: what's currently working

A short list of what the system does today, so future-you can quickly
orient.