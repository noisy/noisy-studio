# Ports and instance selection

| Instance | HTTP/dashboard | Dashboard state WebSocket (`/state`) |
| --- | --- | --- |
| Installed native app | 9765 | 9766 |
| Source development (`scripts/dev_daemon.sh`) | 7765 | 7766 |
| Dashboard hot reload (Vite) | 5173, proxies explicitly to 7765 | `/state` proxied to 7766 |

The WebSocket carries dashboard state only, never audio: a full snapshot on
connect, then patches on change (protocol in
`src/noisy_studio/listener/state_stream.py`). The dashboard polls GET /status
only while it is down; other clients keep using GET /status.

Claude MCP uses stdio through the bundled engine; normal installation needs
no separate MCP network port. Hooks and MCP must select the same daemon.
The packaged integration defaults to 9765 and respects an explicit
`NOISY_STUDIO_LISTENER_PORT`. The Codex preview stores its selected endpoint;
see [codex.md](codex.md). Do not scan ports and silently choose an instance.

Direct source entry points retain 8765 as a compatibility default. Prefer the
dev launcher, which sets 7765 and an isolated configuration explicitly.
An optional source HTTP MCP transport can be configured separately; it is not
part of the desktop installation.
