# Provider limits · issue 152 design review

Synthetic Lab prototypes only. No credential access, provider requests, daemon state, statusline configuration, or production UI changes.

Three alternatives: A compact dashboard overview (recommended), B account cards with all windows, C a row-oriented window ledger. Review density and placement before production implementation. Account-wide limits remain separate from individual conversation budgets and speech spend.

Plan: use shared window fixtures and meter component; build three layouts with local threshold controls; show independent stale, unknown, unsupported states and weekly-only/per-model examples; verify responsive dark/light previews and dashboard type/build.

Threshold controls affect local preview colors only (70% amber / 90% red defaults). Percentage always means USED. Compact summary chooses highest usage among current windows; missing/stale windows are shown in expanded details and never treated as zero. Stale percentages are historical and grey-striped, reset values estimated. Countdown labels are static fixture examples, not live clocks. Existing account labels and unsupported states are illustrative, not verified provider capabilities.

Integration later must classify actual window durations rather than assume primary is five-hour; preserve freshness independently; mark past-reset samples stale until updated; deduplicate account reports from multiple conversations. Official source paths described in the ticket require separate verification/integration. Never use unofficial OAuth endpoints or overwrite the user's statusline.

## Compact revision

New Compact Usage stories place three alternative summaries inside the existing 268px dashboard rail, alongside microphone, spectrum, audio controls, and separate speech costs. Details opens an independent Usage view in the center pane, never Settings. Back restores the conversation.

Usage tabs show overview/history, attribution, and threshold design controls. Synthetic five-minute samples explicitly leave gaps and reset boundaries disconnected. Stale latest samples are historical values, not current capacity. Changing account/window swaps illustrative summary values; no live collection occurs. Attribution stays unavailable because account quota deltas do not establish per-thread contributions. The historical plot illustrates a short observed interval for the chosen quota window, including weekly windows; it is not a full week of data.
