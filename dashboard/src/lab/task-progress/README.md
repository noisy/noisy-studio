# Task progress design lab (#172)

Prototype only. No task collection, daemon calls, production component changes or live review actions.

## Alternatives

- **Overview ledger (recommended):** tab-order rows, consistent information slots; review-ready results have an accent edge and explicit action.
- **Overview cards:** same information, stronger separation between conversations, slightly more scrolling.
- **Detail checklist:** plan order, with owner labels beside each task.
- **Detail owners (recommended):** parent agent and two named specialist groups; makes delegation visible without pretending the list is a runtime hierarchy.
- **Combined expandable:** selected conversation expands inside the fixed-height scrolling panel. The neighboring rail panels remain stationary.

Shared fixture has the four requested core conversations plus completed-without-target and previously-opened results. Stories also cover idle, stale, blocked, just completed and unsupported task reporting. Light/dark are selectable on every variant; narrow overview has dedicated stories.

Task completion bars mean counts of completed tasks, never elapsed time or predicted completion. Unknown data is explicitly unknown rather than zero. Stale means no recent report, not proof that work stopped. Opening a review target records a local visited state only, never approval. Review label and target come from the fixture, not inferred task titles; all links open the local Company Stage preview in a new tab.

The next implementation decision belongs to the user after reviewing these alternatives. Data collection and provider capabilities remain a separate issue.
