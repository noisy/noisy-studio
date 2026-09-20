---
name: local-dev-setup
description: Run the isolated source daemon alongside the installed Noisy Studio app.
---

# Local development

Read `docs/local-development.md` and any stream-specific handoff supplied by
the user. The source checkout serves the live dev instance, so treat restarts
as visible interruptions.

- Production app: HTTP 9765, WebSocket 9766, `~/.config/noisy-coding`.
- Dev launcher: HTTP 7765, WebSocket 7766, `~/.config/noisy-coding-dev`.
- Vite: 5173, explicitly set `NOISY_CODING_DAEMON_URL=http://127.0.0.1:7765`.

Run `uv sync`, then `scripts/dev_daemon.sh`. Check the printed config location;
never let concurrent daemons share a configuration folder. First launch seeds
provider/tuning settings but not conversation history.

Point hooks and MCP at the same explicit dev port. Source MCP should set
`NOISY_CODING_NO_AUTOSPAWN=1`. Do not install duplicate hook sets. Add new API
routes to Vite's `DAEMON_PATHS` and restart Vite after configuration changes.

Before restarting, announce it and request `POST /shutdown` with
`{"delay_seconds":60}`. Let the user postpone or cancel; wait for the port to
free before relaunching. Never kill the daemon. Check its new startup line and
selected microphone afterwards; use the device required by the stream handoff.
Do not touch production, OBS, or stream overlays.

Run appropriate checks before handing off and verify behavior against the
selected running instance. Do not display secrets or full private state.

## Clearing the xAI key to test the no-key path

The settings panel can only *replace* a key, never remove one, so the
"user has not configured anything yet" path cannot be reached from the UI.
Clear it on disk instead.

**Dev instance only.** Production credentials live in
`~/.config/noisy-coding/credentials.json` and are not part of this.

```sh
F=~/.config/noisy-coding-dev/credentials.json
cp -p "$F" /tmp/creds-dev-backup-$(date +%s).json   # take one even if a copy exists
python3 -c "
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d.pop('xai_api_key', None)
json.dump(d, open(p,'w'), indent=2)" "$F"
```

Restore by copying the backup back over it.

**No daemon restart is needed.** The key is read per call, not cached at
startup, so the next speech attempt fails immediately with:

```
No xAI API key configured yet — set it on the dashboard (SETTINGS panel)
```

Two things to know before doing this while anyone is listening:

- **It takes the agent's voice away.** Every `speak` fails until the key is
  restored; the session keeps working in text.
- Inspect the file by **shape**, never by content - key names and value
  lengths are enough to confirm what happened, and a secret that is never
  printed cannot end up in a transcript or on a livestream.
