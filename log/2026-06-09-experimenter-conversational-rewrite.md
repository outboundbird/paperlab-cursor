# 2026-06-09 — Experimenter conversational rewrite (P1, structural)

Shipped the structural rewrite the roadmap had marked as "next build
priority" since 2026-06-05. Two earlier `/experimenter` smoke runs had
shown the agent jumping straight to building on turn 1 — reading both
specs, building the comparison table, deciding the seam, and popping a
multiple-choice menu — without asking the user a single problem-setup
question. Incremental rule-patching (R0/R0a/R0b/R0c) had failed twice.

The pre-rewrite diagnosis (in
[`log/2026-06-05-experimenter-problem-framing-feedback.md`](./2026-06-05-experimenter-problem-framing-feedback.md))
called this a structural problem: skill + agent were *organized
around the deliverable* (`design.md`'s seven-section schema), so
prose rules saying "talk first" read as soft preferences against a
hard build pipeline. Today's session confirmed the diagnosis by
re-reviewing both files together — the methods-comparison frame and
the build-pipeline structure showed up in nine independent places
across the skill and six more across the agent.

This log records the rewrite that resulted, the design decisions
reached in conversation with the user, and the changes shipped.

## Diagnosis (compressed)

Three reinforcing presumptions were baked into the files:

1. **Methods-comparison was the agent's identity.** `experimenter.md`'s
   front-matter description, role section, examples, build sequence,
   and greeting all assumed the experiment was a multi-method
   comparison. R0b's "shared-task check" was downstream of an identity
   that already said "I compare methods" — so any user intent that
   wasn't a comparison was forced into one.
2. **The schema *was* the task model.** Both files loaded the
   `design.md` §0/§0.5/§1/§2/§2b/§3-§7 schema before turn 1, and
   structured everything around filling it. The agent's task became
   "fill the form."
3. **Conversational rules were negative constraints layered on a
   positive build goal.** R0/R0a/R0b/R0c said "don't" — but the
   structure said "do." The positive goal won.

Patching rules in one file could not dislodge presumptions that
appeared in fifteen places.

## Resolution: structural rewrite

### Conversation as the spine, schema as a kit

Two phases now drive the agent:

- **Plan phase** (default, the spine). Open prose dialogue about what
  the user wants to learn or decide. No `AskQuestion` tool, no
  numbered/lettered option menus. The agent may read specs lazily,
  invoke `comparator`, consult `critic_reviews.md` — but **does not
  load the `ml-experiment-design` skill in Plan**, so the schema does
  not bias the conversation toward the form.
- **Build phase** (user-triggered). Realize the plan: write
  `design.md`, invoke `coder` Stage 2, route the critic gate, run.
  `AskQuestion` is allowed here for genuine forks.

### User has the ultimate call on the phase switch

The Plan→Build transition is now an explicit, three-step gate:

1. The user signals the plan is ready ("let's write it up", "go
   ahead", "everything looks good"). Ambiguous signals do not
   qualify; the agent asks in prose when uncertain.
2. The agent **summarizes the plan in chat** — research type,
   hypotheses, criterion, methods, seam (or variant), data setup,
   MVP — and **shows the section list explicitly**:

   > For what we've discussed, I'd write up sections 1, 2, 3, 4,
   > 5.1, 5.2, 5.3, 6, 7, 8 — including the comparison seam (§5.2)
   > since this is a methods comparison between GIBGAT and GIBSR.
   > Does that match what you have in mind?

3. The user confirms both content and structure before the file is
   written.

This was the single most important behavioural change: the agent now
proves it understands the plan before serializing it, and the user
sees both the *what* and the *shape* before the artifact exists.

### Research type is an outcome, not an input

The methods-comparison frame is dropped from agent identity. The
agent's role statement now says it pair-designs experiments without
presuming shape; the **research type** (methods comparison, ablation,
reproduction, sensitivity, exploration, custom) emerges from the
conversation. New `research_type:` front-matter field records it on
each `design.md`.

This unlocks the kit-of-parts schema (next).

### Kit of parts, renumbered §1–§8

The old §0 / §0.5 / §1 / §2 / §2b / §3-§7 numbering is replaced by a
clean §1–§8 with §5 holding sub-sections:

| § | Section | Status |
|---|---|---|
| 1 | Header / front-matter | mandatory |
| 2 | Problem setup | mandatory |
| 3 | Hypotheses | mandatory |
| 4 | Question and criterion | mandatory |
| 5 | Methods | mandatory (parent) |
| 5.1 | Methods used | mandatory |
| 5.2 | Comparison seam (or research-type variant) | conditional |
| 5.3 | Minimum viable comparison | mandatory |
| 6 | Data-synthesis design | mandatory |
| 7 | Decision rationale | mandatory |
| 8 | Uncertainty flags | mandatory |

Two ordering changes vs. the old schema:

- **§3 hypotheses comes before §4 criterion.** Hypotheses are the
  user's predictions in their own framing; the criterion (§4)
  operationalizes the property the hypotheses imply. Predictions
  first, the measurement they imply second.
- **§5 Methods absorbs the seam (was §2b) and the MVP (was §5).**
  Both belong with Methods conceptually — the seam is *how methods
  are placed against each other*; the MVP is the smallest
  cross-method run plan.

§5.1 was reframed: not "native loss" but **how performance is
measured for this experiment** — accuracy, precision, recall, loss,
attribution fidelity — *whatever decides §3*. Measurement is
hypothesis-driven, not method-loss-driven.

§5.2 is **conditional**: present when research type is methods
comparison; replaced by an ablation table, reproduction success
criteria, sensitivity sweep table, or user-defined variant for other
research types. The agent picks the right variant from the kit during
Plan and proposes it to the user.

### Common shapes are reference, not templates

`SKILL.md` now carries a "research type table" — a reference for
which sections the kit needs assembled for each common research type.
**Not a template the agent fills.** The agent assembles the section
list from the kit during Plan, sketches it explicitly to the user,
and writes accordingly. New shapes can be invented mid-conversation;
the agent proposes a structure, the user adjusts, the schema
self-documents the novelty in §8.

### Conversational rules removed from the skill

R0/R0a/R0b/R0c no longer live in `ml-experiment-design/SKILL.md`.
They are absorbed into `experimenter.md` as **positive instructions**:
"open prose questions only", "one topic per turn", "listen before
proposing", "the user moves the session from Plan to Build." The
skill now contains only schema-level rules (front-matter format,
⚠️ UNCERTAIN convention, [A]/[B] prefixes).

This separates the artifact (skill) from the behaviour (agent), so
each file's structure matches its job.

### `AskQuestion` policy

The user clarified the `AskQuestion` policy in conversation: **agent
should ask questions, but open ones — not multiple-choice menus that
enforce the agent's framing**. So:

- **Plan phase:** banned. Multiple-choice (via `AskQuestion` or via
  numbered/lettered prose) presupposes the agent's framing of the
  options and turns the user into a chooser, not a designer. Open
  prose questions only.
- **Build phase:** allowed for genuine forks (e.g. "the critic
  flagged X — fix or document?"). By Build, the design is settled
  and the agent isn't shaping it.

## What shipped

Files written:

- `.cursor/skills/ml-experiment-design/SKILL.md` — full rewrite. Kit
  of parts, renumbered §1–§8, research type table, removed R0–R7,
  added Plan→Build self-checks (user explicitly switched, agent
  summarized + section sketch, user confirmed).
- `.cursor/agents/experimenter.md` — full rewrite. Plan/Build phase
  split, no schema load in Plan, turn-1 open question template,
  positive conversation rules, explicit section sketch +
  user-confirm gate before any file write.
- `ROADMAP.md` — `§2b` references → `§5.2`; experimenter row
  rewritten; P1 status changed from "awaiting user decision" to
  "shipped 2026-06-09".
- `AGENTS.md` — experimenter row rewritten to reflect Plan/Build
  phases and `§5.2` seam reference; coder row's `§2b` → `§5.2`.
- `log/2026-06-09-experimenter-conversational-rewrite.md` — this
  file.

Files checked but not changed:

- `.cursor/skills/ml-experiment-code/SKILL.md` — references the seam
  by name ("seam contract from `design.md`"), not by section number.
  Continues to work.
- `.cursor/agents/coder.md` — same. References "seam contract from
  `design.md`" without section number.
- `.cursor/agents/comparator.md` and
  `.cursor/skills/ml-comparison/SKILL.md` — no §2b / §0.5 references.
- `.cursor/agents/tutor.md` — has a `§2b` reference, but it points
  inside `tutor.md` itself, not into `design.md`. Unrelated.
- Existing logs (`2026-06-04-*`, `2026-06-05-*`, etc.) — left
  unchanged as historical record.

## Smoke validation

Pending. The next `/experimenter <topic>` invocation should reach
turn 1 by greeting + one open question + ending the turn, with no
spec read, no `AskQuestion`, no `comparator` invocation. The schema
should not be loaded until the user has explicitly signalled the plan
is complete and confirmed both the plan summary and the section
sketch.

If smoke fails (agent still skips ahead), the structural change is
not the right level of intervention; we'd reach for a hook or
deterministic pre-emission gate at that point.

## Why this should hold where rule patches didn't

Rule patches were **negative constraints** layered on a positive
build goal. The agent had a clear positive task ("produce
`design.md`") and vague negative restraints ("don't read specs in
depth", "don't pop a multiple-choice menu"). The positive goal won
every time.

This rewrite changes the **positive goal**: in Plan, the goal is
"have a useful conversation about what the user wants to learn,"
with the schema absent from the agent's working memory until the
user invites it in. There is no longer a build pipeline running
underneath the conversation — only the conversation, which sometimes
produces a build pipeline at the user's signal.

The fact that this required reorganizing the skill (not just the
agent) confirms the `2026-06-05` diagnosis: the agent inherits
structure from the skill, so a conversational agent on top of a
schema-shaped skill keeps reverting to schema-shaped behaviour. Both
files had to move together.

## Carry-overs

- Smoke validation, as noted.
- A run with a non-comparison research type (e.g. ablation or
  reproduction) would test whether the kit-of-parts schema works as
  intended, not just for comparisons.
- The `experimenter` row in the agents table now references `§5.2`;
  if downstream agents (coder, future evaluator) acquire explicit
  section-number references, those should track the same numbering.
