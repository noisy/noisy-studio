# Claude inbox delivery

Claude remains one provider with one conversation key, tab, character and
outgoing speech identity. Its private default delivery implementation is the
session inbox. Codex keeps its existing hook delivery.

## Registration and lifecycle

The updated Claude hook reads `CLAUDE_CODE_MESSAGING_SOCKET` from its inherited
environment on SessionStart and UserPromptSubmit and sends it privately with the
hook payload's full session ID. No socket path is derived from an ID. Participant
hooks cannot replace the parent's endpoint. Other hooks still report activity,
turn completion and participant lifecycle, and inject trusted outgoing speech
identity. SessionEnd removes the endpoint.

Endpoints are held only in memory and are never included in dashboard snapshots.
After a daemon restart, an already-idle session has to run an updated hook again:
**type a message in that Claude session, or restart/resume it**. A new session
registers at startup. Update app and plugin together to get the new bundled hook.
A session without an endpoint is shown as requiring registration. No other tab,
same-directory session or process is substituted.

## Delivery and visible outcomes

Completed speech is grouped per original recipient and in original order. The
normal continuation window is 2 seconds; recording extends it up to a 20-second
cap. The sender opens a local Unix connection only when the group is ready and
bounds connect/write operations. The frame includes the exact native session ID
and describes the text as user speech transcribed and delivered by Noisy Studio.
Claude presents this as peer input; our wording does not override host permissions.

The compact content prefix is `[VOICE · Noisy Studio transcript]`. This names
the actual source without repeating a long explanation on every message.
App-generated character notifications keep a separate `[NOISY STUDIO]` prefix.
Claude Code adds its own outer "another Claude session" envelope; Noisy Studio
does not supply or control that text. The currently documented inbox path still
applies peer-message policy, including to scripts and hooks. No documented
alternate message shape that changes this envelope was found in the
[Claude Code messaging reference](https://code.claude.com/docs/en/cross-session-messaging).
Do not impersonate a keyboard prompt or alter inbound controls to hide the wrapper.

Each group includes stable receipt IDs and asks the receiving agent to call
`acknowledge_delivery` after reading. The trusted PreToolUse integration supplies
the receiving session identity; the daemon matches that identity and the IDs
against attempted messages in its durable journal. This is an explicit agent
acknowledgement, not a native host receipt or proof of completed work. A general
reply or later hook activity is not used as confirmation. Missing or failed tool
calls leave the outcome unknown. Host permission rules remain unchanged.

SessionStart/UserPromptSubmit supply the receipt convention through integration
context. Putting that instruction only in the peer message was insufficient in
an ordinary-speech live check: Claude could answer without acknowledging it.
Per-message content now includes IDs only, without repeating the full convention.

**Upgrade existing sessions:** reload/reconnect the Noisy Studio MCP server, or
start a fresh Claude session using the updated integration, so the new tool is
available. Updating only the daemon cannot replace an already-running MCP tool
server. Historical messages without receipt IDs remain unknown; do not resend
them merely to obtain a receipt. No extra acknowledgement is spoken aloud.

- **Queued:** waiting for the continuation window or a usable registration.
- **Sent, unconfirmed:** the socket write completed. This does not establish that
  Claude admitted, read or acted on it; host policy may hold or refuse it.
- **Delivery unknown:** 60 seconds after a completed write, the status settles
  here if no agent acknowledgement has arrived. This is not a failure
  verdict: check the receiving session before deciding to resend. The deadline
  survives daemon restart. Older journal entries without a write timestamp settle
  immediately. Neither timeout nor restart triggers a resend or permits recall.
- **Uncertain, not retried:** a write failed after connection, or the daemon stopped
  during an attempt. The message may already have arrived.
- **Unavailable:** no endpoint, a closed endpoint, or a known connection failure
  before writing. Explicit re-registration can retry that known pre-write failure.
- **Rejected:** local target validation failed, or the message was no longer
  eligible before writing. A wrong target rejected by the host cannot be inferred
  from a successful raw write; it becomes unknown on our side.
- **Confirmed:** the receiving agent called `acknowledge_delivery` for this exact
  message in this session. Late or repeated acknowledgements are safe, including
  after restart or after the status became unknown. A socket completion arriving
  after acknowledgement cannot downgrade the confirmed state. Queued, cancelled
  and wrong-session messages cannot be confirmed. This does not assert completion
  of the user's requested work or require echoing the user's words.

The private `claude-delivery.sqlite3` journal in the selected instance's config
folder commits an attempt before I/O. Restart restores pending speech even when
the periodic history save lagged. Written/uncertain entries are never automatically
replayed. Cancellation is durable and only succeeds before an attempt is claimed.
No automatic hook fallback, blind retries or exactly-once execution is promised.

## Deliberate rollback

Change `CLAUDE_DELIVERY` from `"socket"` to `"hooks"` in
`src/noisy_coding/harness/agent_provider.py`, rebuild if packaged, then restart the
daemon gracefully. Existing sessions must run a fresh SessionStart or Stop hook
(restart/resume the session or complete a typed turn) to create a listener. The
retained async hook registrations have sufficient timeout for this path; in
socket mode the same processes return promptly without starting listeners.

The provider identity and session key stay unchanged. The journal also records
hook pickup attempts during rollback, preventing later socket activation from
replaying them. Previously sent/uncertain speech remains held for inspection;
switching implementations is not permission to resend it.

Do not change inbound controls to conceal a held/refused message, infer a session
from cwd, or expose endpoint/token/configuration values while troubleshooting.
