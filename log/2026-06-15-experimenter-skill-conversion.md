# 2026-06-15 — Experimenter converted to skill + command

Converted the `experimenter` from a Cursor subagent
(`.cursor/agents/experimenter.md`) to an inline skill loaded by a
slash command. The behavioral content was ported faithfully — no
rule changes, only file format and "subagent" wording adjusted.

## Why

The 2026-06-09 conversational rewrite was meant to fix Plan-phase
discipline (no multi-choice menus, explicit Plan→Build gate with
section sketch). A smoke test on 2026-06-12 (transcript:
`Downloads/cursor_experimenter_gib_command.md`, GIBGAT graph
classification) showed the user-visible failures *still* happening:

- Bolded prose option-menus reappeared in Plan phase (turns 4, 5).
- Plan→Build summary was missing the explicit §1–§8 section sketch.
- Two questions in one turn on turn 2.
- Build phase silently dropped 400→150 epochs without asking.

User feedback established the diagnosis: `/experimenter` spawns a
**subagent** that runs in the background while a **parent agent
relays** responses to the chat. What the user sees is the parent's
summary, not the subagent's raw output. So even if `experimenter.md`
was perfect, the relay layer reformatted prose options into bolded
menus and dropped the section sketch when condensing.

That is a Cursor architecture pattern, not something a subagent
prompt can fix.

## Decision: hybrid command + skill

- `.cursor/commands/experimenter.md` — tiny dispatcher; preserves
  the native `/experimenter <topic>` UX.
- `.cursor/skills/experimenter/SKILL.md` — behavioral rules ported
  from the deleted `experimenter.md` agent file. Loaded by the
  command into the **main chat agent**, so there is no subagent
  relay between user and experimenter.
- `.cursor/skills/ml-experiment-design/SKILL.md` — unchanged. Holds
  the `design.md` schema, kit of parts, and verification gate.
  Loaded only when entering Build phase, to keep Plan-phase context
  lean.

The chat hosting `/experimenter` becomes single-purpose for the
duration of the session. To exit, start a new chat. Same UX pattern
as `/tutor`.

## Trade-offs accepted

- **Token cost.** Experimenter skill ≈ 2.8k tokens persistent in
  chat working memory; +4.2k more during Build phase (schema skill).
  ≈ 3.5% of a 200k context. Moderate, not blocking.
- **No tool sandbox.** Skill loads into main agent → full tool
  access. Subagents could be restricted; this is a small regression
  in safety.
- **No background execution.** Skill-driven main agent blocks the
  chat for the duration of the session.
- **No dedicated transcript artifact.** Subagent runs produced a
  separate transcript file; with a skill, everything lives in the
  main chat (still recoverable).

## What did not change

- Behavioral rules. The skill content is a faithful port of
  `experimenter.md` — same phase split, same conversation rules,
  same Plan→Build gate, same scope boundaries. "Backend mode"
  wording for `comparator` / `coder` invocations was changed to
  "subagent invocation" for clarity (those remain subagents
  invoked by the experimenter — only the user↔experimenter layer
  is now inline).
- `ml-experiment-design/SKILL.md`. Untouched.
- `coder.md`, `critic.md`, `comparator.md`. Their references to
  "invoked by the experimenter" still read correctly: the
  experimenter skill (running in the main chat) still drives those
  invocations.

## Files touched

- Created: `.cursor/commands/experimenter.md`
- Created: `.cursor/skills/experimenter/SKILL.md`
- Deleted: `.cursor/agents/experimenter.md`
- Modified: `AGENTS.md` (experimenter row in suite description;
  agent-to-skill mapping)
- Modified: `ROADMAP.md` (experimenter row in agents table; user-
  facing subagents list now distinguishes inline skills + commands)

## Follow-up

- **Re-validate by smoke test.** Run `/experimenter <topic>` in a
  fresh chat. Pass criteria:
  - Turn 1: greeting + one open prose question + end of turn.
  - Plan phase: no `AskQuestion`, no bolded prose option-menus.
  - Plan→Build: explicit user signal + plan summary + §1–§8 section
    sketch + user confirmation before any file write.
  - No relay reformatting (the chat is the experimenter).
- **Ablation/reproduction smoke test.** A non-comparison research
  type would test whether the kit-of-parts schema works as
  intended.
- **Token-budget check.** If the experimenter skill bloats chat
  context noticeably during long sessions, consider a leaner
  rewrite (target ~1.5k tokens) — but only after smoke tests
  validate the structural change holds.

## Carry-overs from the conversational rewrite (2026-06-09)

Still unresolved at the experimenter level:

- Whether the skill format actually carries the no-menu rule and
  section-sketch requirement reliably across a long session, or
  whether they erode under context pressure. Same risk as the
  subagent had, only at a different layer.
- A non-comparison research-type smoke test.
- The 400→150 epoch silent caveat (Build phase did not ask the
  user before changing). Not a Plan-phase issue, but worth
  watching in the next Build run.
