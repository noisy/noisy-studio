# Codex voice integration

The Codex plugin uses the same Noisy Studio daemon as Claude Code. It adds
session registration, speaking, mid-task incoming speech, and idle listening.
No OpenAI API key or OpenAI voice provider is required for this integration.

## Install

Requirements: local Codex with plugin and lifecycle-hook support (tested
with CLI **0.153.4**), [uv](https://docs.astral.sh/uv/getting-started/installation/),
and a running Noisy Studio daemon. `uv` installs the required Python version
and the plugin's pinned Python dependencies. macOS is the validated release host. Other platforms are source development
and are not supported desktop releases.

After this branch is released:

```sh
codex plugin marketplace add noisy/noisy-studio
codex plugin add noisy-coding@noisy-coding
```

For a clean checkout before release, register the checkout instead. Use a
checkout without `.venv` or `node_modules`: local marketplace installation
copies the plugin directory, including local dependency caches.

```sh
codex plugin marketplace add /absolute/path/to/noisy-coding
codex plugin add noisy-coding@noisy-coding
```

Start a new Codex session and ask: **“Use Noisy Studio to set up voice.”**
The dedicated skill guides configuration and verification. Existing Claude
installation and unrelated Codex hooks/MCP entries remain intact.

Select the daemon you intend to use:

| Installation | Default HTTP port |
| --- | --- |
| Desktop app | 9765 |
| Development | 7765 |

These are defaults, not routing rules. Custom ports are supported. If
multiple instances run, choose one explicitly. The plugin never scans and
silently chooses another instance. Start a daemon using the desktop app or
the [existing installation guide](INSTALL.md) if none is running.

The setup command, run from the installed plugin root, is:

```sh
uv run --frozen python scripts/install_codex.py --port 9765
```

It writes only `~/.config/noisy-coding/codex.json`; both hooks and MCP read
that file. `NOISY_CODING_CODEX_CONFIG` can select another settings file and
`NOISY_CODING_LISTENER_PORT` is an explicit endpoint override. Do not set a
shared `NOISY_CODING_AGENT_NAME=codex`: sessions must remain distinct.

## Review hooks and verify both directions

Open **`/hooks`** in Codex and inspect the `noisy-coding` definitions. Trust
the hooks you intend to run. Installation does not grant hook trust, and
changed definitions need review again. No permission bypass flags are needed.

| Event | Action |
| --- | --- |
| SessionStart / UserPromptSubmit | Register this session and report activity |
| PreToolUse | Report activity; overwrite speech-call identity with this session ID |
| PostToolUse | Deliver queued voice as model context |
| Stop | Wait for voice and continue the turn when it arrives |

Start a new session after endpoint changes so MCP uses the same endpoint as
the hooks. Complete provider setup and microphone/speaker permission in the
selected daemon's dashboard. Ask the agent to speak, then answer aloud.
Both messages must appear under the intended agent tab. A working `/status`
response or a queued utterance alone does not prove a working round trip.

## Why Codex can look busy while listening

**The synchronous Stop hook holds the turn open for up to one hour.**
It is waiting for your next spoken message, not generating tokens the whole
time. To shorten that wait, run:

```sh
uv run --frozen python scripts/install_codex.py --port 9765 --listen-seconds 60
```

Use `--listen-seconds 0` to disable idle listening while preserving mid-task
voice. The next hook process reads the change; an already-running listener
retains its original timeout. When the window expires, start another turn
to listen again. This plugin does not install an idle queue/wake service.

## Identity and troubleshooting

The trusted PreToolUse hook replaces `agent_id` on speech calls. It never
accepts an identity invented by the model. Registration and draining use
the same session ID. The MCP process can therefore be shared across
sessions; directory names and shared environment variables do not route
Codex speech. A missing identity produces a tool error and, when reachable,
a dashboard error event. Review `/hooks` instead of hardcoding another name.
Claude and Codex both require identity supplied by their trusted host hooks. A duplicate listener reports its conflict in Codex
and the dashboard, and exits without consuming another listener's queue.

If speaking fails after first installation, ensure `uv` is on the PATH
visible to Codex and start a new session. The MCP configuration uses a
plugin-relative `cwd` and relative arguments; `${PLUGIN_ROOT}` is expanded
for hooks, but not MCP arguments in the tested Codex version. If voice only works one way,
verify hook trust and that both directions selected the same daemon. Do
not install a second global hook set alongside the plugin. If you used
the earlier manual prototype, remove only its `noisy-coding` entries after
reviewing them; keep unrelated hooks.

The dashboard uses registered agent labels and a “New conversation” fallback. Legacy
history fields such as `role: "claude"` remain compatible with older daemons;
they no longer determine the chat heading.

## Remove or update

Before removing the plugin, remove its integration settings from its root:

```sh
uv run --frozen python scripts/install_codex.py --uninstall
codex plugin remove noisy-coding@noisy-coding
```

Removal preserves unrelated Codex configuration and the daemon's voices,
credentials, and history. Stop listening in the old session or close it;
removing a plugin does not retroactively cancel an already-running hook.
Use `codex plugin marketplace upgrade noisy-coding` to refresh a tracked
marketplace, reinstall through the plugin browser, and review changed hooks.

Technical references: [Codex hooks](https://learn.chatgpt.com/docs/hooks),
[plugin packaging](https://developers.openai.com/plugins/build/plugins).
