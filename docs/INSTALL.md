# Install Noisy Studio

The supported release is the native macOS Apple Silicon app. Download it from
[GitHub Releases](https://github.com/noisy/noisy-studio/releases), move
**Noisy Studio.app** to `/Applications` or `~/Applications`, then open it.
The signed app includes its engine and dependencies.

Choose speech providers in the app. Enter credentials only in its settings.
For local providers, allow the initial model download; cached models work
offline. Grant microphone access to **Noisy Studio Engine** when prompted.
Input Monitoring is needed for the optional global hotkey, not ordinary startup.
Select the intended microphone and speaker and verify their levels.

## Claude Code

```sh
claude plugin marketplace add noisy/noisy-studio
claude plugin install noisy-coding@noisy
```

Restart Claude Code, review the installed hooks, and ask for voice setup.
The plugin runs MCP and lifecycle hooks through the app's bundled executable;
no host Python or uv is needed. The app must be running on port 9765.
`NOISY_STUDIO_ENGINE` can explicitly select another engine for development;
`NOISY_CODING_LISTENER_PORT` selects its daemon endpoint. These integration
processes never start another audio daemon.

Ask the agent to speak, answer aloud, and confirm both messages appear under
the intended conversation. A healthy HTTP endpoint alone does not prove audio.

## Codex preview

See [the dedicated guide](codex.md). This preview still requires uv for its
hook/MCP processes and explicitly selects the app endpoint during setup.

## Updates and troubleshooting

Update the app and plugin together, then start a new coding session. An older
app may not support the plugin's bundled integration entry points. If tools
report that the app is missing, check the installation location and update it.
Hooks fail open when the app is absent so normal coding can continue.

If microphone access fails, check System Settings > Privacy & Security,
reconnect the device and reselect it in the app. Do not disable Gatekeeper or
remove quarantine as a routine installation step. Report a rejected signed
release with its version instead.

Keep production and development separate: [ports](ports.md),
[local development](local-development.md), [hook delivery](hooks.md).
