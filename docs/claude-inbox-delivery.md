# Claude hook delivery with socket wake-up

Claude remains one provider, conversation, character and tab. **Hooks are the
only consumer of actual speech.** The socket is a wake-up mechanism, not a second
speech-delivery path. Codex keeps its existing hook implementation.

## Normal delivery

The daemon queues completed utterances for their original recipient. Existing
PostToolUse and SessionStart/Stop listeners pick them up using the established
hook flow, including the listener's continuation grouping. The dashboard marks
speech delivered at hook pickup, as before. This means handed to the integration,
not proof that the model read it or completed the requested work.

If speech remains queued after the 2-second quiet window plus a 1-second pickup
allowance, the provider requests a socket wake-up. Recording extends that window
up to the existing 20-second continuation cap. The control message contains only
a short wake token; it never contains the speech or a receipt instruction.

Claude Code fires UserPromptSubmit for an admitted socket prompt. The hook sends
that prompt to the daemon, which matches the exact stored wake token and canonical
session, and drains speech through the same queue path. It returns the actual
speech as additional context. If another hook already consumed it, or it was
cancelled, the hook blocks the empty wake without starting another model response.
Ordinary user prompts and wakes belonging to another session are not intercepted.

No model receipt tool is advertised. Actual speech has no receipt-ID suffix and
there are no acknowledgement instructions at registration or on each message.
Previously cached receipt tools remain compatible with the old HTTP endpoint.

## Registration, failure and restart

SessionStart/UserPromptSubmit register the inherited socket endpoint and full
native session ID privately. Subagent hooks cannot replace parent registration.
No path is guessed from a UUID, cwd or another tab. SessionEnd removes the endpoint.

Endpoints remain in memory. After a daemon restart, type a message in the target
session or restart/resume it to register again. Updated hook scripts are required
for wake pickup; update the integration together with the daemon. Existing hook
listeners can continue delivering speech even when socket wake is unavailable.

The journal records each wake before socket I/O and permits only one pending
wake per session. Daemon restart does not blindly repeat an ambiguous write.
An explicit session restart allows a new control wake; old controls remain
recognizable so a late arrival can be handled without duplicating speech.
Actual queue pickup and cancellation remain atomic in the core. Completed hook
pickups are journaled so restart does not put already-delivered speech back into
the queue. A journal failure after pickup leaves its pre-pickup claim, preventing
replay. Hidden or ended sessions are not woken.

A socket write never marks speech delivered. A refused/held wake leaves speech
queued for a hook; a failed connection leaves it queued and reports the problem.
Host inbound controls are unchanged. Claude's peer envelope is host-owned.

Historical messages already sent by the earlier direct-socket implementation
are not requeued: they may already have caused work. Their old unknown status
cannot be resolved by sending them again.

## Internal selection

`CLAUDE_DELIVERY = "hook-wake"` in `harness/agent_provider.py` is the default.
`"hooks"` disables independent socket wake while retaining the original hook flow.
The earlier `"socket"` implementation is retained for comparison/regression
coverage, not used for normal delivery. There is no transport settings UI or
automatic switch to direct-socket speech delivery.
