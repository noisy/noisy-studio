# Provider limits · compact renewal comparison

Four design-only stories render the actual App.vue with synthetic conversation fixtures: Thin Bars (inline reset), Thin Bars Secondary Reset, Thin Bars Reset Legend, and preserved Three Columns. Bold Bars is removed. A lab-only Teleport inserts the summary into the real left rail and removes its targets on unmount.

Claude and Codex show Session/Weekly; Grok shows a shared Weekly plan pool. Every percentage and countdown is fictional, explicitly marked “demo” in the header. No account credentials, real usage, provider requests, or production UI integration are involved. Account icons and extra account labels are omitted.

Each renewal caption is keyboard focusable with exact local date/time in its tooltip and accessible label. Countdown values are a frozen illustration, not a running clock. Nonpositive reset intervals say “Awaiting update”; stale history is labelled historical rather than presented as current capacity. All summaries represent account-wide allowances, not per-conversation budgets.

Details remains a separate Usage center pane with Back, synthetic sampled history, disconnected reset/gap segments, and unavailable attribution. Account delta data cannot prove per-thread consumption.

## Sources supplied by parent research, 2026-09-27

- Claude official statusline: https://code.claude.com/docs/en/statusline — `rate_limits.five_hour` / `seven_day` and `resets_at`. Each window can be independently absent. Model-specific Opus data was not confirmed for this collector, so it is not shown by default.
- Codex official app-server: https://learn.chatgpt.com/docs/app-server — `account/rateLimits/read`, updated notifications, `usedPercent`, `windowDurationMins`, `resetsAt`. Windows are nullable; classify by duration, never assume primary means five-hour.
- Grok plan FAQ: https://docs.x.ai/grok/faq — shared weekly subscription allowance including Build, with reset date/time in Settings Usage. A supported programmatic collector is NOT verified. The fixture demonstrates layout, not a live integration claim.
- Grok API limits are a separate concept: https://docs.x.ai/developers/rate-limits — per-model requests per second/tokens per minute, not this subscription weekly pool.
