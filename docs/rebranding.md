# V3 technical rename and upgrade guide

V3 makes a clean break from **noisy-coding** to **noisy-studio**. There are no old-name CLI aliases, Python import shims, environment fallbacks, automatic data moves, or dual plugin registrations. Existing data is never deleted by the rename. Upgrade the app and integrations together.

## Name mapping

| Before V3 | V3 |
| --- | --- |
| Python distribution `noisy-coding` | `noisy-studio` |
| Python imports `noisy_coding` | `noisy_studio` |
| `noisy-coding-mcp`, `noisy-coding-listener`, `noisy-coding-mobile` | `noisy-studio-mcp`, `noisy-studio-listener`, `noisy-studio-mobile` |
| `NOISY_CODING_*` | `NOISY_STUDIO_*` |
| MCP/plugin registration `noisy-coding` | `noisy-studio` |
| Engine executable `noisy-coding-daemon` | `noisy-studio-daemon` |
| `.config/noisy-coding` or desktop `.config/noisy-coding-app` | `.config/noisy-studio` |
| `.config/noisy-coding-dev` | `.config/noisy-studio-dev` |
| Electron profiles `Noisy Coding`, `Noisy Coding Dev` | `Noisy Studio`, `Noisy Studio Dev` |
| Renderer preference keys `noisy-coding.*` | `noisy-studio.*` |
| App IDs `pl.noisy.coding.companion[.dev]` | `pl.noisy.studio.companion[.dev]` |

The engine app identity was already `pl.noisy.studio.engine` and is unchanged. The shell's new identity may need fresh OS permissions. Test the signed upgrade before release; source tests cannot prove macOS permission continuity. The repository and public links use `noisy/noisy-studio`; the domain remains `noisystudio.ai`. No Docker or browser-audio deployment is supported.

## Instructions for an agent assisting with an upgrade

1. **Inventory without exposing secrets.** Identify the actual running app, source checkout, daemon ports and selected config directory. Do not assume an old default: previous desktop builds used more than one config path. Inspect names/counts or the startup config-location line, not credential values or full history. Keep dev and production separate.
2. **Stop writers before copying.** Quit the old app. For the live dev daemon use `POST /shutdown` with `{"delay_seconds":60}` and respect postponement/cancellation; wait for the port to become free. Stop/reload associated integrations before replacing their registration. Never copy an actively written SQLite database in isolation from its WAL, or run two daemons against the same store.
3. **Choose data migration explicitly.** Back up the selected complete configuration directory with its permissions, then copy it to the canonical destination only if that destination does not exist. Copy the whole directory, including databases and their sidecars. Do not merge two existing stores or overwrite a newer destination; ask which store to use. Alternatively, set `NOISY_STUDIO_CONFIG_DIR` to the existing directory and reuse it in place. For source dev, use `NOISY_STUDIO_DEV_CONFIG_DIR` with `scripts/dev_daemon.sh`. This explicit override is supported regardless of the folder's spelling.
4. **Install the complete V3 bundle.** Replace the app as a unit, including its engine; do not mix old and new shell/engine executables. For source development, run `uv sync` from the updated checkout so the old distribution is removed and the new entry points are installed. Avoid co-installing old and new distributions in the same Python environment. Rename every configured environment key using the mapping above; old keys are ignored.
5. **Replace the integration once.** Update Claude/Codex plugin and MCP registration to noisy-studio, use the new commands/bundled engine, and update the endpoint override. Remove the old owned registration and hooks; preserve unrelated tools and hooks. Do not install a second copy alongside the old one. Existing MCP processes and agent sessions need reconnect/restart to discover the new tool names. The source Codex settings file is now `.config/noisy-studio/codex.json`; change an old installer-owned `managed_by` value to `noisy-studio` in the copied file before using the installer again. Review `docs/codex.md` and `docs/hooks.md` for current setup.
6. **Carry over UI preferences if wanted.** The new Electron profiles start fresh. With both old and new apps stopped, back up and copy the old profile only into an absent new profile; never overwrite or merge a running Chromium profile. Local preference keys for accent, agent accent, avatars and audio cues now use `noisy-studio.*`; explicitly copy the corresponding old-key values if preserving them, with new values winning. Other cached UI state can be recreated. A fresh profile is also valid.
7. **Verify the actual application.** Confirm the config location and microphone selection, existing conversation/history counts, provider setup, app/engine version agreement, and one spoken round trip. Check one hook set per session and the expected MCP server name. Dev uses 7765/7766; the app uses 9765/9766. Vite defaults to the dev daemon, and `NOISY_STUDIO_DAEMON_URL` selects a custom endpoint. Request any new OS permissions normally; never bypass security prompts.
8. **Keep rollback possible.** Retain the old app, original data/profile backups and registration description until verified. Roll back the whole app/integration pair, restore old environment keys and select the original store. Do not run both generations against the same store. No public push, installation, account setting change or communication is implied by this guide; act within the user's actual authorization.

## Current development session

The running dev instance's existing store is explicitly retained during the rollout. A new default directory must never be mistaken for lost history. The Vite endpoint was corrected to default to port 7765 after its old environment key stopped being recognized. This session's old MCP registration may remain loaded until the host reconnects; that does not imply that the V3 package supports old names.

## Historical material

This document intentionally names old identifiers to explain the upgrade. Git history and already published issue/PR text are not rewritten. Historical images and recorded media may contain the former name; do not claim a complete frame/audio audit from a source-text scan. The local checkout directory can retain its existing name without affecting imports or builds.
