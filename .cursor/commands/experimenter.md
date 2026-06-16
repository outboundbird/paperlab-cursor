---
name: experimenter
description: Start or resume an experimenter pair-design session anchored to a problem class.
---

# /experimenter

Load the `experimenter` skill at `.cursor/skills/experimenter/SKILL.md`
and apply it to the topic given as the command argument.

Usage:

- `/experimenter <topic>` — start or resume an experiment design for
  problem class `<topic>`.
- `/experimenter` — resume the most recent experiment.

`<topic>` is **verbatim user input** — never normalize, lowercase, or
pluralize. If it is not a valid path segment, ask the user for an
alternative.

After loading the skill, follow it from the top: enter Plan phase,
greet, ask one open question, end the turn.

This command reshapes the current chat into an experimenter session.
The chat is now anchored to that topic for its duration. To exit
experimenter mode, start a new chat.
