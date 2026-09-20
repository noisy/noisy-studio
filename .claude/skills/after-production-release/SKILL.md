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
