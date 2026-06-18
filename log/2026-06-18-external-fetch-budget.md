# 2026-06-18 — External fetch budget rule

Closed roadmap §2 External-data access by shipping the
`external-fetch-budget.mdc` rule. The MCP half of §2 was zero-work
(`firecrawl` already configured; `arxiv` MCP is conditional and not
yet triggered).

## Five design questions and the answers

Settled in chat before writing the rule:

1. **Budget-bearers.** `tutor`, `explainer`, `comparator`, `critic`.
   Pipeline agents (`acquirer`, `dissector`, `experimenter`,
   `coder`, `evaluator`) work from already-gated upstream artifacts
   and do not carry the budget.
2. **What counts.** `firecrawl` MCP, `WebSearch`, `WebFetch`. Cache
   hits and local PDF extraction (`tools/pdf.extract_pdf_text`) do
   **not** count.
3. **Unit.** Per session, with a soft per-task awareness. Both
   counters tracked.
4. **Threshold + enforcement.** Soft cap, self-tracked, no hook.
   **Per session: 20.** **Per task: 7.** On either threshold, the
   agent stops and asks the user. **Reset rules are asymmetric**
   (revised after a same-day post-write review surfaced a bug in
   the original symmetric design):
   - Task threshold confirmation → only task counter resets;
     session counter keeps rising.
   - Session threshold confirmation → both reset (global
     override).
   The original "both reset on any confirmation" design defeated
   the session cap entirely (k tasks × 7 fetches each could never
   trigger session=20 if every task confirmation reset session to
   0). The asymmetric reset keeps the session budget as a real
   constraint only the user can lift. User chose "more generous"
   budget over the roadmap's original "max ~5 per concept" guess.
5. **Preferred fetch order.** Paper text + `spec.md` first (free),
   then arXiv abstract, then one blog, then author/lab page. Never
   crawl whole sites.

## Task-definition fix (same-day, post-confirmation)

A second post-write review surfaced a related bug: the original
task list included `<concept>-<slug>.md` (an explainer-written
backend intermediate per `AGENTS.md`) alongside `<concept>.md`
(the tutor's user-facing artifact). Since both `tutor` and
`explainer` are budget-bearers, treating each intermediate as its
own task could spend 2 × 7 = 14 task fetches on a single user
request "explain concept X." Fix: **a task is one user-facing
artifact or one user-facing turn**; backend intermediates roll
into the parent task's counter (same applies to
`synth__<a>__<b>-<slug>.md`). Rule updated; explainer fetches now
count toward the parent tutor task counter explicitly.

## Implementation choice — rule only, no agent edits

The rule uses `alwaysApply: true`, so it loads in every chat
without per-skill plumbing. Cleaner than threading a "see the
external-fetch-budget rule" line into each budget-bearer's skill
or agent file. If a budget-bearer's behavior needs tuning later,
edit the rule, not the agents.

The reporting line ("*Fetches: N task / M session.*") is the only
behavioral thread the rule asks of the agents — easy to forget,
but visible in chat when present.

## Files touched

Created:

- `.cursor/rules/external-fetch-budget.mdc` — the rule.
- `log/2026-06-18-external-fetch-budget.md` (this file).

Edited:

- `ROADMAP.md` § Planned units → §2: MCP marked zero-work; rule
  marked shipped 2026-06-18 with one-line summary + log pointer.
- `ROADMAP.md` § Reference: what's currently working: rule added
  to the Rules list.

## Status of roadmap §2

- **MCP — `firecrawl`:** already configured (no work needed).
- **MCP — `arxiv` (conditional):** still not triggered. Revisit if
  structured arXiv metadata becomes a recurring need (the citation
  verifier already covers metadata for citation checks).
- **Rule:** **shipped.**

## Next step (unchanged)

A2 — production-flow re-validation of `/experimenter`, deferred per
the user's decision earlier this session. After A2, the closest
remaining items are §3 reindex v2 (gated on a larger paper corpus)
and the parked `coder` verifier gate sub-decision.
