> Historical analysis from before the native integration overhaul.
> For current setup, use INSTALL.md, hooks.md and codex.md.

# Agent integration: why it is fragile, and how to rebuild it for 3.0

**Status:** analysis, 2026-09-10. Input for the 3.0 stabilisation work.
Facts below were read from the code on `v3-desktop` (47d4c7c), the open
issues, `issues-drafts/`, Krzysztof's OpenBot notes
(`~/life/research/openbot-2026-09-09.md`) and the Claude Code docs
(client here: 2.1.267).

## 1. The symptoms Krzysztof reports

1. After ~1 h idle the agent cannot be woken by voice.
2. A freshly started Claude session is not connected until the user types a
   first message.
3. After a break / daemon restart / Claude restart the agent's replies show
   up in a NEW hash-labeled tab; input and output diverge (#40,
   `session-id-rotation-tabs.md`).
4. Messages reach sessions that were not the addressee (#40).
5. Tabs derive "alive/dead" from heartbeats, a guess we should not need.
6. Nobody but the user notices any of this - there is no test that would.

## 2. How the integration works today (one paragraph)

Five Claude Code hooks (`hooks/*.py`) each POST `/register` + `/activity`
to the daemon on every call; PostToolUse also GETs `/drain` and injects
voice as `additionalContext`; Stop polls `/drain` every 0.5 s for up to
`REWAKE_WAIT_SECONDS=3600` under `asyncRewake`, exits 2 to wake the agent
or exits 0 silently on timeout (`hooks/stop.py:28,130-164`). The MCP
server (`src/noisy_coding/server.py`) is a thin messenger for `speak`;
it resolves its identity separately from the hooks. The dashboard tab ==
the flat `agent` string; liveness is inferred from heartbeats
(`AGENT_OFFLINE_AFTER_SECONDS=180`, `state.py:38`).

## 3. Root causes (not symptoms)

### R1. Identity is inferred, twice, from different sources
- Hooks: `NOISY_CODING_AGENT_NAME` -> stdin `session_id` -> `"default"`
  (`hooks/_agent_identity.py:60-62`).
- MCP: `NOISY_CODING_AGENT_NAME` -> env `CLAUDE_CODE_SESSION_ID` -> cwd map
  (`server.py:34-52`).
- The cwd map (`sessions.json`) is one entry per directory, last writer
  wins; two sessions in one repo overwrite each other.
- `_agent_identity.MAP_FILE` ignores `NOISY_CODING_CONFIG_DIR`
  (`_agent_identity.py:20` vs `config_dir.py:15`): hook and MCP can read
  different files.
- Docker: hook cwd is the host path, MCP cwd is `/app`; the only link is
  `${CLAUDE_CODE_SESSION_ID:-}` which may be empty (`hooks/mcp_exec.sh:30`).
- Registration is a *side effect of every hook call*, not a lifecycle
  event. There is no SessionStart hook at all, so a session that has not
  run a turn does not exist for the daemon (symptom 2).
- When the MCP id is unknown the daemon auto-creates a tab labelled
  `agent[:8]` (`http_api.py:92-110`) - that IS the ghost tab (symptom 3).

### R2. "Wake" is emulated by blocking a hook for an hour
- Stop hook = long-poll. When it times out (3600 s) nothing wakes the
  session ever again until the user types (symptom 1).
- It only exists after a turn has ended, so it cannot cover the fresh
  session case (symptom 2).
- One rewake lock per agent (`rewake-{AGENT}.lock`), code comments already
  reference an unsolved lock problem (#53).
- Whether Claude Code caps hook `timeout` is undocumented. Setting it to
  days is an experiment, not a design.

### R3. Subagents run the same hooks with the same session_id
- Claude Code delivers `agent_id`/`agent_type` in hook payloads for
  subagents; our hooks never read them. A subagent's PostToolUse therefore
  drains the parent's queue (`/drain?agent=<session_id>`) and injects the
  voice into the *subagent's* context. **Hypothesis for #40** - the main
  thread never saw the message because a child consumed it. Verify with
  one spawned Agent + one spoken sentence.
- The daemon-side "subagent is a participant" doctrine
  (`http_api.py:39-48`) covers *speaking*, not *listening*.

### R4. Addressee is stamped, not enforced
- Transcripts are stamped with the tab at recording start, unstamped ones
  go to `active_agent` (`state.py:803-808`). "DELIVERED" means "some
  process drained it", not "the addressee received it".
- The wrapper text urges the recipient to act (#40).

### R5. Liveness is inferred from heartbeats
- Two independent liveness signals (drain heartbeat, activity line) and a
  180 s threshold. Every value is a compromise between a false "offline"
  and a stale "online". With a real lifecycle (session start/end events)
  none of this is needed.

### R6. No executable contract
- `tests/unit/test_codex_hooks.py`, `test_server_identity.py` test pieces.
  Nothing simulates: start -> speak before first turn -> resume with a
  rotated id -> subagent drains -> 61 min idle -> Claude restart -> daemon
  restart. Every one of those is a bug we found by ear.

## 4. What Claude Code offers today (facts, with caveats)

| Mechanism | Wakes idle session? | Mid-turn delivery? | Session identity | Caveats |
|---|---|---|---|---|
| Stop hook + `asyncRewake` (today) | until timeout only | no (PostToolUse does) | `session_id` in stdin | undocumented cap; deaf after timeout |
| **Channels** (`notifications/claude/channel`) | **yes, any time the session is open** | queued, delivered together on next turn | the MCP process IS per session | research preview, v2.1.224+; needs `--channels` / `--dangerously-load-development-channels server:<name>` at launch; custom servers not on the allowlist during preview; Pro/Max fine, Team/Enterprise need admin switch; Bedrock/Vertex excluded; no ack from Claude |
| SessionStart hook (`startup/resume/clear/compact/fork`) | n/a | n/a | `session_id`, `source`, `cwd`, `transcript_path` | **we do not use it**; cheapest fix for symptom 2 and for resume/rotation |
| `agent_id` in hook payloads | n/a | n/a | distinguishes subagent from parent | **we ignore it**; fix for R3 |
| Agent SDK (`query()` with streaming input, OpenBot model) | yes, push into stdin | yes (`steer`) | we mint the session id | headless: no TUI for the user; SDK sessions hidden from `claude --resume` picker; two writers on one JSONL if mixed |
| `claude --bg` + `attach` | n/a | n/a | printed id | spawn path for #53, not a wake path |
| Cross-session `SendMessage` | yes | yes | needs a Claude sender | heavy; not for a daemon |

Channels detail (from the reference): capability
`capabilities.experimental['claude/channel']: {}`, notification
`notifications/claude/channel` with `content` and `meta` (identifier keys
only); the model sees `<channel source="<server>" ...>text</channel>`;
optional reply tool; `instructions` string is injected as context on
connect. Only requirement is an MCP server over stdio - the protocol is
plain JSON-RPC, so the Python server can emit it (needs checking that the
Python `mcp` package lets a server send a custom notification and declare
an experimental capability).


Channels timeline (changelog): introduced in 2.1.80, still "research
preview" at 2.1.267 (~190 releases later), only fixes and permission relay
since. No public graduation date - assume months. Routes to production
users: (a) submit the plugin to `claude-plugins-official/external_plugins`
to get on the curated allowlist, (b) Team/Enterprise admins can allowlist
it today via `allowedChannelPlugins`, (c) Pro/Max: development flag only.
Design consequence: channels = best available wake, Stop long-poll = the
fallback that must never go silent.

### Codex (checked 2026-09-10, CLI 0.154.0)

No push into an idle interactive TUI session exists. MCP notifications are
logged, never shown to the model (openai/codex #18056, #15299, #17543);
a channels-equivalent request was closed "not planned" (#17101); #35542
states the TUI is the only surface local tooling cannot reach. Stop hook
can `{"decision":"block"}` to force a continuation, default timeout 600 s,
`async` hooks cannot wake an idle session. The headless path is
`codex app-server` (JSON-RPC over stdio/ws: `thread/start|resume`,
`turn/start`, `turn/steer`, `turn/interrupt`), which is exactly what
OpenBot drives. So for Codex the harness layer has two adapters too:
`codex-hooks` (today, long-poll, no push) and `codex-app-server`
(spawned, full control). The provider abstraction is therefore not
optional - the two harnesses have different wake capabilities and the
daemon must know which it has.

## 5. Proposed shape: an agent-harness provider layer

Mirror `src/noisy_coding/providers/` (TTS/STT `Protocol`s, lazy registry,
explicit capabilities, invariants stated in `base.py`). New package
`src/noisy_coding/harness/` (name open):

```
harness/
  base.py        # contracts below, provider-agnostic errors
  __init__.py    # registry: "claude-hooks", "claude-sdk", "codex"
  claude_hooks/  # today's hooks + SessionStart + agent_id + channel push
  claude_sdk/    # OpenBot-style spawned session (#53), later
  codex/         # existing lifecycle adapter, moved
  fake.py        # in-memory simulator used by the contract tests
```

Contract (`base.py`):

- **Identity**: `ConversationKey` - one stable key per human-visible
  conversation, chosen by the adapter, never by the daemon. For Claude:
  `transcript_path` (stable across resume; a fork gets a new one), with
  `session_id` as alias. Daemon keeps an alias table: any id seen for the
  same key is the same tab. Ghost tabs become impossible by construction.
- **Lifecycle events** the adapter must emit: `session_started(source)`,
  `session_ended`, `turn_started`, `turn_ended`, `activity(line)`,
  `subagent_started(agent_id, parent)`, `subagent_ended`,
  `title_changed(title)` - the user renames a session in Claude
  (`/rename`) and the tab must follow (Krzysztof 2026-09-10: part of the
  contract). Claude adapter: read the last `customTitle` from
  `transcript_path` on each hook (host-readable now that Docker is gone;
  `hooks/exec.sh` mining becomes unnecessary); SessionStart also carries
  `session_title`. A daemon-side manual label must not be overwritten by a
  fallback (`session_id[:8]`), only by a real title. Tab liveness =
  "between session_started and session_ended", no heartbeat guessing.
  Where a harness cannot emit `session_ended` (Claude has no SessionEnd we
  can trust for crashes), the adapter declares `capabilities.liveness =
  "heuristic"` and the daemon falls back to heartbeats *only for that
  adapter*.
- **Delivery**: `deliver(message, addressee) -> receipt`. Exactly one
  recipient; a subagent hook never drains, it forwards to the parent;
  `receipt.delivered_to` names the conversation; the dashboard shows
  UNDELIVERED until a receipt exists.
- **Wake capability**: `capabilities.wake in {"push", "long_poll", "none"}`
  plus `max_idle_seconds`. The daemon picks the best available: channel
  push when the session was started with channels enabled, Stop long-poll
  otherwise, and *tells the user* which one it has (the "deaf after an
  hour" state must be visible on the tab, not silent).
- **Spawn** (optional capability): `spawn(cwd, opening_message)` -
  `claude --bg` for hooks, `query()` for SDK.

Contract tests (`tests/harness/`): one parametrised suite that runs the
same scenarios against `fake.py`, `claude_hooks` (driving the hook scripts
with synthetic stdin, including `agent_id`, `source=resume`, rotated ids)
and `codex`. Scenarios = section 6 list. No dashboard, no Claude binary,
no microphone.

## 6. Scenarios the contract must pass (today's bug list as tests)

1. Speak arrives before any hook (fresh session) -> lands in the right tab,
   not a hash tab.
2. `SessionStart source=resume` with a new session_id -> same tab.
3. Daemon restart -> tabs, order and identity survive (registry persisted,
   not only `active_agent`).
4. Claude restart in the same cwd -> same tab, marked "resumed".
5. Subagent PostToolUse -> parent receives the message, child does not.
6. Two sessions in one cwd -> two tabs, no overwrite.
7. Idle 61 min -> either still wakeable (push) or the tab visibly says
   "not listening" (long-poll); never silent.
8. Message addressed to tab A -> tab B never sees it; receipt names A.
9. `NOISY_CODING_CONFIG_DIR` set -> hooks and MCP agree.
10. Docker: host cwd vs container cwd -> identity still matches.

## 7. Sequencing proposal for 3.0

1. **Quick, contained fixes on the current hooks** (days): add
   SessionStart hook (register + alias on resume), read `agent_id` and
   route subagent drains to the parent, key tabs by transcript_path with
   alias table, persist the registry, fix `MAP_FILE`/`CONFIG_DIR`, show
   "listening / not listening" on the tab. Each with a scenario test.
2. **Harness contract + fake + move hooks/codex under it** (a week): no
   behaviour change, tests become the spec.
3. **Channel push adapter** (experiment first, half a day): Python MCP
   server declares `claude/channel`, daemon pushes voice through it; test
   with `--dangerously-load-development-channels server:noisy-coding-dev`.
   If it works, the Stop long-poll becomes the fallback, not the core.
   Blocker for end users: allowlist during preview -> track, and ask
   Anthropic about listing the plugin.
4. **SDK adapter** (#53 spawn path) after 3.0 unless channels fail.

## 8. Tabs (Krzysztof, 2026-09-10)

Requested behaviour, independent of the above but enabled by R1/R5:
browser-like - new tab always appended on the right, user reorder
(drag-and-drop nice to have, dashboard too), no alive/dead heuristics
(alive first, then ended; ideally an ended Claude session can be
*resurrected* from the tab via `claude --resume <id>` / `--bg`), and
per-position hotkeys (F1 = tab 1 + PTT, F2 = tab 2 ...), see #49.

## 9. Open questions to verify empirically (30 min each)

- Does `CLAUDE_CODE_SESSION_ID` in the MCP env really differ from the hook
  `session_id` after resume, or only after `/clear` / MCP respawn?
- Can a Python `mcp` server declare `experimental` capabilities and emit a
  custom notification? (If not: a 40-line Node shim in the plugin.)
- Do subagent hooks fire with the parent's `session_id` + an `agent_id`?
- Does a hook `timeout` of 86400 behave, or is there a hidden cap?
- Does `SessionStart` accept `asyncRewake` (a listener from second zero)?

## 10. Experiment results (2026-09-10, Claude Code 2.1.267, `claude --bg`, haiku)

Scratch project with logging hooks; raw log in the session scratchpad
(`exp1/log/`).

- **Subagent hooks carry the parent's `session_id` plus `agent_id` and
  `agent_type`** (SubagentStart, PreToolUse, PostToolUse, SubagentStop all
  had `agent_id=ae5366ae...`, `session_id` identical to the parent's). R3
  is confirmed: today a subagent's PostToolUse drains the parent's queue.
  Fix: skip `/drain` (and `/register`) when `agent_id` is present, or
  forward to the parent key.
- **`SessionStart` accepts `asyncRewake`.** The hook slept 90 s, exited 2
  with a stderr instruction, and the idle session ran a new turn and
  answered `REWAKE-OK`. A voice listener can therefore start at second
  zero of a session, before any user message. Symptom 2 is fixable inside
  the hooks.
- **Stale rewake listeners are not killed.** After three turns, three
  `longstop.py` processes from three separate Stop events were alive at
  once (pids 55880, 56113, 58542). Claude Code never terminates a previous
  `asyncRewake` hook when a new turn starts. Any design with long-lived
  Stop listeners must make old listeners stand down themselves (the
  current flock does that only partially, see #53 notes in `stop.py`).
- **Hook `timeout` cap:** experiment running (`timeout: 86400`, heartbeat
  every 30 s); result to be appended when the process passes 3600 s.

## 11. Triage (Krzysztof + Claude, 2026-09-10)

Easy (hours, each with a scenario test): E1 skip drain/register when
`agent_id` present (#40); E2 SessionStart hook = register + listener from
second zero; E3 `MAP_FILE` via `config_dir`; E5 visible "not listening"
state instead of silent timeout, and the dashboard tells the user what to do
(type anything in the terminal / restart the session) - the daemon knows the
state, the frontend owns the message; E6 new tab always appended right.
Dropped: rewording the `[VOICE]` wrapper - a symptom patch; with E1 + F3
mis-delivery cannot happen by construction, and a short "ok" fits any
conversation anyway. Keep the wrapper neutral, nothing more.

Feasible (days, under the harness contract): F1 conversation key =
transcript_path + alias table; F2 persistent tab registry; F3 delivery
receipt naming the recipient; F4 stale listeners stand down; F5 liveness
from lifecycle events; F6 dropped - Docker is not supported in 3.0 (decision 2026-09-10); F7 tab reorder +
per-position hotkeys (#49); F8 Codex short listen window; F9 fake harness
+ contract suite (first commit).

Uncertain: U1 hook timeout cap (running); U2 channels push; U3 SDK session
shared with the terminal; U4 resurrect a dead session from its tab, including the "deaf" case:
can the daemon run `claude --resume <id>` (or `--bg --resume`) while the
user's terminal still holds the session, and what happens to both?; U5
`CLAUDE_CODE_SESSION_ID` rotation after resume.

Impossible in the hooks model: X1 wake idle Codex TUI (app-server adapter
instead); X2 mid-turn delivery without a tool call (SDK/app-server steer);
X3 channels for Pro/Max without the dev flag (submit plugin upstream).

Order agreed: F9 -> E1..E6 as first scenarios -> F1..F5.

## 12. Assumptions the code still protects that are obsolete (CONFIRMED by Krzysztof 2026-09-10 - drop all five)

1. **Separate config dir for dev vs prod** (`NOISY_CODING_CONFIG_DIR`, E3) -
   Krzysztof 2026-09-10: nice if cheap, not important; he uses two Claude
   profiles anyway. Demote E3.
2. **Identity per config** (`NOISY_CODING_AGENT_NAME` work/personal,
   TODO.md 2026-07-09) - superseded by identity per session. Candidate for
   removal.
3. **cwd -> agent map as MCP fallback identity** (`sessions.json`) - the
   source of the two-sessions-one-repo collision. Unnecessary if identity is
   injected per call: the Codex path already does `PreToolUse ->
   updatedInput.agent_id` (`hooks/codex.py:72-75`, enforced by
   `NOISY_CODING_REQUIRE_AGENT_ID`). Claude Code PreToolUse supports
   `updatedInput` too, so the MCP server can stop resolving identity at all.
   This alone removes most of R1.
4. **Docker as the flagship install path** - DECIDED 2026-09-10: 3.0 drops
   Docker support entirely; native apps, macOS first. Host-vs-container
   constraints (cwd, transcript path, `exec.sh` title mining, `mcp_exec.sh`)
   no longer shape the design and may be cut in 3.0 wherever they get in
   the way.
5. **Synchronous Stop hook for harnesses without async rewake** - removed
   for Claude; still what Codex runs (3630 s, blocking the turn, hence the
   stuck keyboard messages). Decide: short window (F8) or none.

### Codex: is there a "typed message waiting" signal? (probe, 2026-09-10, codex-cli 0.153.4)

No. Verified in source and by experiment over `codex app-server`: a steer
or a second `turn/start` during a blocking Stop hook produces no hook, no
notification and no rollout append; `UserPromptSubmit` for the queued
message fires 0.35 s *after* the Stop hook exits, for both messages
together - exactly the observed symptom. `async: true` Stop hooks cannot
continue the turn (exit 2 ignored). So for `codex-hooks` the only lever is
the length of the synchronous window (default now 30 s), plus the `deaf`
state on the tab. A real fix needs either an upstream hook at enqueue
time or a noisy-coding-owned app-server client (`codex --remote`).

### U1 resolved: no hidden hook-timeout cap (experiment, 2026-09-10)

A Stop hook registered with `timeout: 86400` ran continuously for over 65
minutes (heartbeat log, three async-rewake processes still alive at
65 min) with no sign of a Claude Code cap at 30 or 60 minutes. So the
"deaf after ~1 h" symptom was NOT a platform limit - it was our own
`REWAKE_WAIT_SECONDS=3600`: the poll loop exited at 60 min and nothing
relit it. The harness contract fixes this two ways: `max_idle_seconds` can
be set well beyond an hour (the hook timeout follows it), and when a
listener does expire the tab goes visibly `deaf` instead of silently
unreachable. Recommendation for 3.0: raise the Claude default to several
hours; keep the deaf state as the honest fallback.

### Dashboard should treat /status as authoritative (observed 2026-09-10)

After the daemon was restarted onto the new key scheme (tab key changed
from session_id to transcript_path), an open dashboard briefly showed TWO
tabs with the same label - the stale old-key tab plus the new one. The
daemon only ever had one; the client had merged its last render with the
new /status instead of replacing. The stale tab had no live conversation,
so it could not be selected, only closed. Fix (part of phase 5 dashboard
wiring): render the tab strip from /status.conversations as the single
source of truth and drop any tab absent from it, rather than merging. A
one-time migration artifact, but the merge behaviour would also strand a
tab after any future daemon restart until a manual refresh.

### Dashboard transport: one WebSocket state stream (Krzysztof, 2026-09-10)

The dashboard polls /status; every tab-state bug today surfaced as "the
strip is stale/wrong until refresh". Krzysztof's call: the daemon should
push ONE WebSocket event stream (conversations, utterances, activity,
status) and the dashboard should render from it, with /status only as the
initial snapshot. The WS bridge on port+1 already exists for tab audio;
extend or sibling it. Part of the phase-5 dashboard wiring.

### Ops lesson: launch the dev daemon only through scripts/dev_daemon.sh

A hand-launched dev daemon (2026-09-10 16:00) came up WITHOUT
NOISY_CODING_CONFIG_DIR, so it ran on the production config dir: an empty
registry, "all tabs gone", and a stray conversations.json written into
the production dir. The script sets port AND config dir together; never
start the daemon by hand with an ad-hoc env.

### Idea (Krzysztof, on stream 2026-09-13): tell the agent what was heard

When the user interrupts a spoken reply, the agent should learn which
part of its sentence was actually heard and which was cut - so it can
resume or rephrase only the unheard part instead of repeating or dropping
it. The daemon knows the cut point (bytes played / streaming progress);
delivering it with the next [VOICE] message is the cheap version. Not
scheduled; noted for a ticket when Krzysztof wants one.
