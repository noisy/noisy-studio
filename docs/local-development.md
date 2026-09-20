# Local development

The installed app owns 9765/9766 and `~/.config/noisy-coding`. Development uses
7765/7766 and `~/.config/noisy-coding-dev`. Never share configuration folders
between running instances. Check the dev launcher's startup line before
interpreting persisted state. Do not print credentials or private configuration.

```sh
uv sync
scripts/dev_daemon.sh
```

The launcher builds a missing dashboard and, on first use only, seeds provider
and tuning settings into a separate dev folder. Conversation history stays
isolated. Set `NOISY_CODING_DEV_CONFIG_DIR` for a different dev folder.

## Dashboard

```sh
cd dashboard
npm ci
NOISY_CODING_DAEMON_URL=http://127.0.0.1:7765 npm run dev
```

Open port 5173 for hot reload. New backend routes must be added to
`DAEMON_PATHS` in `vite.config.ts`; otherwise Vite may return HTML with status
200. Restart Vite after proxy configuration changes. Build with `npm run build`
to update the daemon-served dashboard.

## Integrations

For a source Claude MCP process, set `NOISY_CODING_LISTENER_PORT=7765` and
`NOISY_CODING_NO_AUTOSPAWN=1`, then run `uv run noisy-coding`. Source hooks use
`uv run python hooks/claude_hook.py` with the same port. Configure one hook set
per session; duplicate hooks can consume each other's queued messages.
Do not edit private host configuration while on stream.

For a frozen-engine test, set `NOISY_STUDIO_ENGINE` to the built executable
and run `sh hooks/native.sh mcp` or `sh hooks/native.sh hook`. These modes
never open audio hardware or start a daemon. Their explicit listener port must
match the instance being tested. The Codex setup script can select 7765;
see [codex.md](codex.md).

## Restarting the live dev daemon

```sh
curl -fsS -X POST http://127.0.0.1:7765/shutdown \
  -H 'Content-Type: application/json' -d '{"delay_seconds":60}'
```

The user may postpone or cancel. Wait for the port to free before relaunching
`scripts/dev_daemon.sh`; if cancelled, leave the existing instance running.
Never kill it. Verify the new startup line and selected microphone after the
restart. During a stream, follow the supplied handoff and notify the stream
agent; do not touch overlays or production.

## Checks

Run Python unit/harness tests, dashboard tests/build, and relevant desktop
checks. Build the engine with `cd desktop && npm run build:daemon`, then run
`scripts/smoke_integrations.py` from the repository root via uv with the engine
executable as its argument. See [desktop-app.md](desktop-app.md) for packaging.
