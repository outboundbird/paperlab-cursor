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
   agent stops and asks the user; on confirmation, **both counters
   reset** (checkpoint model — not a hard cap). User chose
   "more generous" budget over the roadmap's original "max ~5 per
   concept" guess.
5. **Preferred fetch order.** Paper text + `spec.md` first (free),
   then arXiv abstract, then one blog, then author/lab page. Never
   crawl whole sites.

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
