---
name: setup
description: Set up and verify Noisy Studio voice through its native desktop app.
---

# Noisy Studio voice setup

The supported installation is the macOS app with its companion Claude plugin.
Use `docs/INSTALL.md` for installation. No host Python or uv is required for
Claude: `hooks/native.sh` runs MCP and lifecycle hooks using the bundled engine.
Keep the app and plugin updated together. Codex preview has a separate setup
flow in `docs/codex.md`, including its current uv prerequisite.

1. Confirm the app is installed in `/Applications` or `~/Applications` and open.
2. Use the intended endpoint: native app 9765, explicitly selected dev 7765.
   Never scan and silently switch instances. Custom ports require explicit
   configuration shared by hooks and MCP.
3. Ask the user to choose providers and audio devices in the app. Credentials
   are entered there, never in chat. Local providers download models once.
4. Confirm microphone permission for Noisy Studio Engine. Global-hotkey Input
   Monitoring is optional. Check the intended microphone and output device.
5. Review the plugin hooks in the host and start a fresh session after endpoint
   or plugin changes. Avoid duplicate hook installations.
6. Speak briefly, then have the user answer aloud. Verify both directions and
   the intended conversation tab. A status endpoint or queued message alone
   does not prove audio playback or delivery.

If the app is missing, MCP explains how to install it; hooks fail open to avoid
interrupting ordinary coding. The integration process never starts a daemon.
For debugging, report only selected harmless status fields, never entire
configuration files, credentials, histories, or process command lines.
