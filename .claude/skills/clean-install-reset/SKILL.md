---
name: clean-install-reset
description: Plan a scoped native Noisy Studio reset while protecting user data.
---

# Native installation reset

Determine whether the problem concerns the app, plugin, or a selected dev
instance. Prefer reinstalling the app and matching plugin while retaining
settings. Resetting configuration or deleting history requires explicit user
approval for those concrete paths and data; explain what will be lost first.

Before any approved reset, gracefully close the affected instance and preserve
a backup of its configuration without printing its contents. Production uses
`~/.config/noisy-studio`; the standard dev launcher uses
`~/.config/noisy-studio-dev`. Do not reset both by inference. Do not remove
session state or lock files while an instance is running.

Reinstall the native app from an appropriate signed release, update the host
plugin, and start a fresh host session. Reconfigure providers in the app only.
Verify microphone permission, selected devices, running version and voice in
both directions. Follow `docs/INSTALL.md`. During a stream, never open private
host settings or display credentials, and obey the delayed dev restart rule.
