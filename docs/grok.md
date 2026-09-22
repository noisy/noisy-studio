# Grok voice integration

Grok uses the same Noisy Studio daemon and the same harness contract as
Claude Code and Codex. The delivery mechanism is private to the Grok
provider. Today that mechanism is the lifecycle hooks, because Grok does
not expose an agent inbox socket or a channel the daemon can write to.

## What the hooks do

| Event | Action |
| --- | --- |
| SessionStart / UserPromptSubmit | Register this session and report activity |
| PreToolUse | Report activity; overwrite speech-call identity with this session id |
| PostToolUse | Deliver queued voice as model context |
| Stop | Wait for voice and continue the turn when it arrives |
| SubagentStart / SubagentStop | Record the child. A child never drains and never listens |

Speech that arrives mid-turn is delivered on the next tool call. Speech
that arrives after a turn is delivered by the Stop hook, which holds the
turn open. A transcript is picked up on the next poll, about half a
second after the daemon has it.

## Install

From a checkout, with the daemon already running:

```sh
uv run --frozen python scripts/install_grok.py --port 9765
```

Use `--port 7765` for the development daemon. The command writes
`~/.config/noisy-studio/grok.json` and `~/.grok/hooks/noisy-studio.json`.
It does not edit other hook files or the MCP configuration. Point the
`noisy-studio` MCP server at the same port. Start a new Grok session,
speak, and answer aloud. Both sides must show on the same dashboard tab.

`--listen-seconds 0` disables idle listening and keeps mid-turn delivery.
The maximum is 3600. The Stop hook timeout is the window plus 30 seconds.
While the hook is listening, a typed message waits behind it, same as Codex.

## Limits that belong to Grok

- After eight voice replies in one turn, Grok ends the turn and ignores
  the Stop hook until the next typed message. That count is Grok's, and a
  typed message resets it.
- An allowing UserPromptSubmit hook cannot attach context. Speech that
  arrives while nothing is listening waits for the next tool call.
- There is no push wake of a fully idle session. A background task or
  timer inside the session can wake it, but only if that session started
  the task. Headless mode starts a new process.
- A subagent is not given its parent's session id, so it does not get its
  own listening tab and it does not take the parent's queue.

A future inbox, socket, or channel would replace the wait inside this
provider. The contract the rest of the daemon sees would stay the same.

## Remove

```sh
uv run --frozen python scripts/install_grok.py --uninstall
```

Removal deletes only the settings and hook file this installer owns.
