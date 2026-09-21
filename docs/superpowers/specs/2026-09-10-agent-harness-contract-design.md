# Agent-harness contract

## Scope and acceptance

Noisy Studio talks to agent systems (Claude Code today, Codex today, an SDK
or channel adapter tomorrow) through one contract, the way it already talks
to TTS/STT engines through `providers/`. Adding a harness means one
directory that implements the contract plus one line in a registry; the
same contract test-suite runs against every registered harness without a
daemon, a microphone, a dashboard or a live agent.

Accepted when the ten scenarios in `docs/agent-integration-analysis.md`
§6 pass as tests, the daemon routes speech and tabs through the contract,
the Claude and Codex hook scripts are thin clients of it, and the five
obsolete assumptions (§12 there) are gone from the code. Docker is out of
scope: 3.0 does not support it.

## Vocabulary

- **Harness** - an agent system and the way we are attached to it:
  `claude-hooks`, `codex-hooks`; later `claude-channel`, `claude-sdk`,
  `codex-app-server`.
- **Conversation** - what the user sees as one tab. Has exactly one
  **key**, chosen by the harness adapter, stable for the life of the
  conversation, plus any number of **aliases** (other ids the harness may
  present for the same conversation, e.g. a rotated session id).
- **Participant** - a subagent inside a conversation. Speaks with its own
  persona, never listens on its own.
- **Listener** - a process that can wake the agent (today: the Stop hook
  poller). A conversation has zero or one *current* listener.

## Architecture

```
hooks/                      thin clients: read stdin, POST raw payload, print
  claude_hook.py              what the daemon told them to print
  codex_hook.py
  _client.py                  HTTP helpers, fail-open rules

src/noisy_studio/harness/    the contract (pure Python, no daemon imports)
  base.py                     dataclasses + Harness protocol + errors
  __init__.py                 REGISTRY: name -> factory; names(); get()
  claude_hooks/adapter.py     Claude Code hook payloads -> contract
  codex_hooks/adapter.py      Codex hook payloads -> contract
  fake/adapter.py             scriptable harness + session driver for tests

src/noisy_studio/listener/
  conversations.py            ConversationRegistry (keys, aliases, order,
                              listener state, persistence)
  http_api.py                 /harness/event, /harness/listener; /speak and
                              /drain resolve ids through the registry
  state.py                    keeps using the flat agent string - that
                              string IS the conversation key
```

Rule: `harness/` imports nothing from `listener/`. Adapters are pure
functions of their input; the daemon hosts them. That is what makes the
contract testable in isolation.

## The contract (`harness/base.py`)

```python
Wake = Literal["push", "long_poll", "none"]
Liveness = Literal["events", "heuristic"]

@dataclass(frozen=True)
class Capabilities:
    wake: Wake                    # how an idle agent learns of a message
    max_idle_seconds: float | None  # long_poll only: after this the agent is deaf
    liveness: Liveness            # can we trust session_started/ended?
    mid_turn_delivery: bool       # can messages reach a turn in progress?
    spawn: bool                   # can the daemon start a new session?

@dataclass(frozen=True)
class Event:
    kind: Literal["session_started", "session_ended", "turn_started",
                  "turn_ended", "activity", "title_changed",
                  "participant_started", "participant_ended"]
    conversation: str             # the key
    aliases: tuple[str, ...] = ()  # ids that also mean this conversation
    title: str = ""               # title_changed / session_started
    source: str = ""              # session_started: startup|resume|clear|compact|fork
    participant: str | None = None  # participant_* and activity from a subagent
    detail: str = ""              # activity one-liner

@dataclass(frozen=True)
class Interpretation:
    conversation: str
    events: tuple[Event, ...]
    may_drain: bool               # False for participants - they never take the queue
    speech_identity: str | None   # what the hook must inject into speak calls
    listener: Literal["none", "start", "poll"]  # what the calling hook should do next

@dataclass(frozen=True)
class Delivery:
    context: str                  # text for the model (additionalContext / stderr)
    system_message: str           # one line for the human in the terminal
    exit_code: int                # 0 = inject, 2 = wake (harness-specific)

class Harness(Protocol):
    name: str
    label: str
    capabilities: Capabilities
    def interpret(self, payload: dict) -> Interpretation: ...
    def deliver(self, messages: list[str], moment: Literal["mid_turn", "wake"]) -> Delivery: ...
```

Errors: `HarnessError` (bad payload, fail closed for speech identity),
never anything harness-specific leaking upward.

Invariants the contract tests enforce for every registered harness:

1. Every payload of one session interprets to the same conversation key.
2. A payload with a participant id yields `may_drain=False`, the parent's
   key and a `participant`.
3. A resume/rotation fixture yields the original key with the new id in
   `aliases`.
4. A title fixture yields exactly one `title_changed` with the title.
5. `capabilities.wake == "long_poll"` implies `max_idle_seconds` set;
   `"none"` implies `listener == "none"` on turn end.
6. `deliver()` output for `wake` has `exit_code == 2` when
   `wake == "long_poll"`, and its `context` contains every message once.
7. `speech_identity` is never derived from cwd or process environment.

### Claude adapter

Key = `transcript_path` (stable across resume; a fork gets its own).
Aliases = `{session_id}`. Title = last `customTitle` in the transcript
(host-readable now), also `session_title` from SessionStart. `agent_id`
present -> participant events, `may_drain=False`, and no `/register` of a
new tab. `hook_event_name` mapping: SessionStart -> session_started
(`listener="start"`), UserPromptSubmit -> turn_started, PreToolUse ->
activity (+ `speech_identity` for `mcp__noisy-studio*__speak|announce|
change_voice|set_speaker_style`), PostToolUse -> activity("THINKING…")
(+ `may_drain`), Stop -> turn_ended (`listener="start"`), SubagentStart/
Stop -> participant_*. Capabilities: `wake="long_poll"`, `max_idle_seconds`
= the configured window, `liveness="heuristic"` (no reliable
session_ended), `mid_turn_delivery=True`, `spawn=True` (`claude --bg`,
later).

### Codex adapter

Key = `session_id`. Title = `"<label> · <id[:8]>"`. Same event mapping;
Stop is synchronous there, so `listener="poll"` with a short window
(default 30 s) and `wake="long_poll"`, `mid_turn_delivery=True`,
`spawn=False`.

### Fake adapter

`FakeHarness` with a `FakeSession` driver: `start(source)`, `prompt()`,
`tool(name)`, `subagent(agent_id)`, `stop()`, `rename(title)`,
`rotate_id()`, `end()`. Each call returns the payload a real client would
send, so the same driver feeds adapter tests, registry scenarios and the
HTTP integration tests. Capabilities are constructor arguments so tests
can model a push harness, a deaf one, or one without spawn.

## Daemon: ConversationRegistry (`listener/conversations.py`)

Owns what `state.py` today spreads over `_agents`, `_agent_labels`,
`_agent_activated`, `_agent_manual_pos` and the flock in `stop.py`:

- `resolve(id) -> key | None` through the alias table.
- `apply(interpretation)` - upserts the conversation, records aliases,
  title, harness name, `last_event`, position (new conversations append at
  the right end), participants.
- `status(key)`: `live` (turn in progress), `idle` (listener current and
  within `max_idle_seconds`), `deaf` (no current listener, or listener
  expired - the dashboard tells the user what to do), `ended`
  (session_ended, harness with `liveness="events"` only). The heartbeat
  heuristic survives only for `liveness="heuristic"` harnesses and only to
  distinguish `live` from `idle`.
- Listener lease: `listener_started(key, listener_id) -> current_id`,
  `listener_alive(key, listener_id) -> bool`, `listener_stopped(key,
  listener_id, reason)`. The newest listener wins; a poller whose id is not
  current stands down on its next poll (replaces the flock, F4).
- Delivery receipt: `drain` returns transcripts only to the resolved key
  and stamps the utterance `delivered to <key>` (F3). Participants get
  nothing.
- Persistence: `CONFIG_DIR/conversations.json` (keys, aliases, titles,
  harness, order, created_at, last_event). Reloaded at boot; nothing is
  deleted by time - only hidden by the user (#71).

`state.py` keeps its `agent: str` parameters; the value is always a
resolved key. `register_agent`/`dismiss_agent` become thin wrappers during
the transition and go away when the dashboard reads `/status.conversations`.

## HTTP surface

- `POST /harness/event {harness, payload}` -> `{conversation,
  may_drain, speech_identity, listener, listener_id?}`. One call per hook
  invocation; the daemon applies the events itself.
- `GET /drain?conversation=<key>&listener=<id>` -> `{transcripts, nudge,
  stand_down: bool}`. `stand_down=True` when the listener is not current.
- `POST /harness/listener {conversation, listener_id, state: started|
  stopped, reason}` - Stop hook start/timeout; timeout flips the tab to
  `deaf` (E5).
- `/speak` requires `agent` to resolve through the registry; unknown ids
  with a known `agent_fallback` keep the participant reattachment, unknown
  ids without one are refused with a loud event - no auto-created hash
  tabs.
- `/register`, `/activity` stay for one release for old hook installs,
  routed through `resolve()`.

## Hook scripts

One script per harness, dispatching on `hook_event_name`, ~100 lines:
read stdin, `POST /harness/event`, act on the answer (`listener="start"`:
start the poll loop with the returned `listener_id`; `may_drain`: drain
and print the `Delivery`; `speech_identity`: print `updatedInput` with
`agent_id`). Configuration: SessionStart, UserPromptSubmit, PreToolUse,
PostToolUse, Stop, SubagentStart, SubagentStop registered in
`hooks/hooks.json` and by `hooks/install.py`; SessionStart and Stop with
`asyncRewake` and a timeout of `max_idle_seconds + 30`.

The MCP server drops `_cwd_agent`, `NOISY_STUDIO_AGENT_NAME` and
`_register_agent`; `agent_id` becomes required for identity-sensitive
tools on every harness (today's Codex behaviour, `NOISY_STUDIO_REQUIRE_AGENT_ID`
becomes the only mode).

## Testing - atomic, in this order

1. `tests/harness/test_contract.py` - parametrised over
   `harness.names()`; the seven invariants above against recorded payload
   fixtures in `tests/fixtures/harness/<name>/*.jsonl`. Claude fixtures
   come from the 2026-09-10 experiment (session start, prompt, Agent tool,
   subagent Bash, Stop, resume). A new harness ships its fixtures with its
   adapter; the suite fails until it does.
2. `tests/harness/test_conversations.py` - the ten scenarios against
   `ConversationRegistry` driven by `FakeSession`, in-process, with a fake
   clock. No HTTP.
3. `tests/integration/test_hook_scripts.py` - each hook script as a
   subprocess against a fake daemon endpoint (the existing
   `test_codex_lifecycle.py` pattern): exit codes, `updatedInput`
   injection, stand-down when not current, fail-open when the daemon is
   down.
4. `tests/integration/test_daemon_harness.py` - real `ListenerState` +
   registry + HTTP handler, driven by `FakeSession` payloads over HTTP.
   Proves the wiring, not the logic.

Layers 1-3 need no daemon. A harness is considered supported when 1 passes
with its own fixtures; it is considered wired when 4 passes.

## Out of scope for this spec

Channels push adapter, SDK/app-server adapters, spawn UI (#53), tab
history UI (#71), per-position hotkeys (#49). The contract leaves room
for each (capabilities, `spawn`, `session_ended`), nothing more.
