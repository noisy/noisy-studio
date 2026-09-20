# Claude receipt evidence — #131

Environment: macOS, Claude Code 2.1.278, source Noisy Studio provider and MCP
server. Receiving sessions used temporary settings/configuration, an independent
temporary HTTP daemon, explicit hook registration, `--setting-sources ''` and
`--strict-mcp-config`. They did not register tabs on the live dev daemon.

## Findings

- A receipt instruction solely in the peer-message body was insufficient:
  ordinary speech could receive an answer without the acknowledgement tool call.
- After SessionStart/UserPromptSubmit supplied the integration convention, fresh
  `claude -p` sessions acknowledged ordinary grouped speech. Both original
  utterances reached confirmed in the intended session. The synthetic spoken
  request did not ask for acknowledgement; the integration handled it.
- A fresh interactive terminal session also produced an acknowledgement and a
  confirmed daemon card while an unsent keyboard draft was present. Submitting
  the draft subsequently showed its marker. The terminal parser did not identify
  an assistant reply marker for that draft, so this does not independently prove
  completion of the draft's requested response.
- Unit checks cover wrong-session and never-attempted-message rejection,
  idempotence, late receipts after timeout/restart, grouped IDs, and the race where
  a receipt arrives before the sender records socket completion. Confirmation
  cannot be overwritten by that later sent state.
- The packaged MCP smoke check now requires the acknowledgement tool as well as
  speech tools, preventing a source-only implementation from passing packaging.

The receipt is an explicit model acknowledgement, not a native Claude socket
acknowledgement and not proof of completed work. If the model does not call the
tool, the tool is unavailable/denied, or receipt storage is unavailable, the UI
must remain unconfirmed/unknown. No automatic resend follows missing evidence.
Existing MCP processes must reload the updated integration. Historical messages
without receipt IDs remain unknown.
