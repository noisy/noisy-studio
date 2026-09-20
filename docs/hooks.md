# Agent hooks

Claude's plugin manifest routes lifecycle events through `hooks/native.sh hook`.
The launcher finds the installed Noisy Studio Engine bundle and enters its
`--integration hook` mode. Source development can call `hooks/claude_hook.py`
directly. Both execute the same adapter and shared harness flow.

The app owns audio capture/playback. Hooks only register sessions, report
activity, attach trusted identity to speech tools, and deliver queued input.
They default to the app on 9765; an explicit listener-port override selects
development. They do not launch an audio daemon.

| Event | Responsibility |
| --- | --- |
| SessionStart | Register the conversation |
| UserPromptSubmit | Register/refresh activity and consume pending input |
| PreToolUse | Report activity and bind speech-tool calls to trusted session identity |
| PostToolUse | Deliver queued voice while work continues |
| SubagentStart / SubagentStop | Track child-agent lifecycle |
| Stop | Listen for voice and continue the conversation when input arrives |

The session ID is the routing identity. Display labels and transcript paths are
not interchangeable with it. The daemon's harness contract resolves parent
and child identities and owns the queues. Unsafe labels are sanitized before
display; a fallback label does not alter the session's routing identity.

Hook stdout is host protocol output, stderr carries wake messages when the
host requires them, and exit codes must survive the launcher unchanged.
Missing app or unreachable daemon must not break ordinary coding. A speech
call with a conflicting identity must not be routed to somebody else's tab.

Configure one hook set per host session and restart sessions after changing
integration endpoints. To verify delivery, ask for speech, respond aloud, and
check the intended tab. Inspect only non-sensitive status fields when debugging.
[Codex](codex.md) uses its own host adapter and idle-listening timeout.
