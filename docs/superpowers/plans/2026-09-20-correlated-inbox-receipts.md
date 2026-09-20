# Correlated inbox receipts (#131)

Implement the full receiving-side flow, not another status workaround.

Each grouped socket delivery carries its stable journal message IDs and asks the
receiving agent to call `acknowledge_delivery` after reading. The tool identity
is supplied by the existing trusted PreToolUse integration, never inferred from
cwd. The daemon matches both canonical session and message ID before confirming.
This is an explicit agent acknowledgement of receipt, not a host receipt or proof
that requested work completed. Missing acknowledgement remains unknown.

- [x] Implement durable, idempotent acknowledgements in the provider, including
  late acknowledgement and the race where acknowledgement beats send completion.
- [x] Add the MCP tool and daemon endpoint, and include the tool in trusted hook
  identity injection. Keep the ordinary voice prefix short.
- [ ] Test cross-session rejection, queued-message rejection, grouped messages,
  restart, late receipt, and no replay. Exercise real Claude sessions with isolated
  settings, MCP and temporary daemon; no test tabs on the live instance.
- [ ] Run required checks, commit, and deploy through the postponable restart.
  Report any required MCP reload explicitly. Do not push or close tickets.

No permission-policy changes, implicit success based on activity, or automatic
retry. Historical messages without receipt metadata cannot be retroactively
confirmed. A refreshed integration is required for the new MCP tool.
