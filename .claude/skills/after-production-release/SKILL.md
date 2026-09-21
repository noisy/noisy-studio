---
name: after-production-release
description: Verify the installed native app and agent integration after a release.
---

# After a native release

Check the intended release's assets and signing/notarization results. Install
or update the native app only within the user's requested scope, preserving
settings and history. Update the companion plugin to the matching release and
start a new host session so its MCP and hook processes use the new engine.

Verify the running app reports the expected version. Test a spoken reply and
an incoming voice message in the intended conversation; inspect the microphone
selection and confirm no unexpected second instance is handling input.
Codex preview should retain its explicitly selected endpoint.

Keep production and development separate. A source checkout update does not
update an installed app. A plugin update does not replace the app's engine.
Never print private host settings, credentials or process command lines.
If restarting the live dev daemon, use the postponable 60-second shutdown and
wait for its port to free. Respect cancellation.

## Upgrading past the plugin rename (#122)

The plugin is `noisy-studio`. It was `noisy-studio` until 3.0, and an
existing install does **not** rename itself.

**Uninstall the old one before installing the new one.** Two registrations
means two sets of hooks on every event - duplicated activity lines,
duplicated listeners, and speech delivered twice.

```sh
claude plugin uninstall noisy-studio@noisy
claude plugin install noisy-studio@noisy
```

Codex, same shape:

```sh
codex plugin remove noisy-studio@noisy-studio
codex plugin add noisy-studio@noisy-studio
```

A user who skips the uninstall sees the agent answer twice and has no
obvious reason why, so say it in the release notes rather than only here.

The daemon accepts **both** MCP tool prefixes (`mcp__noisy-studio__speak`
and `mcp__noisy-studio__speak`) so a stale install keeps its voice until
the user gets round to it. That tolerance is deliberate and should outlive
one release, not be cleaned up immediately.
