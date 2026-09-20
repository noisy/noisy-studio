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

- **Queued:** waiting for the continuation window or a usable registration.
- **Sent, unconfirmed:** the socket write completed. This does not establish that
  Claude admitted, read or acted on it; host policy may hold or refuse it.
- **Uncertain, not retried:** a write failed after connection, or the daemon stopped
  during an attempt. The message may already have arrived.
- **Unavailable:** no endpoint, a closed endpoint, or a known connection failure
  before writing. Explicit re-registration can retry that known pre-write failure.
- **Rejected:** local target validation failed, or the message was no longer
  eligible before writing. A wrong target rejected by the host cannot be inferred
  from a successful raw write; it remains unconfirmed on our side.
- **Confirmed:** reserved for an actual correlated application receipt. The native
  socket currently supplies no such receipt; normal production delivery never
  claims this state or asks Claude to echo every message.

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
