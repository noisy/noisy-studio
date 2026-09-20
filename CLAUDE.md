# Noisy Studio

Native desktop voice coding app. Internal package and plugin names remain
`noisy-coding`; user-facing copy says Noisy Studio.

## Development

Read `.claude/skills/local-dev-setup/SKILL.md` and `docs/local-development.md`.
The installed app uses HTTP 9765, WebSocket 9766, and the production config
folder. `scripts/dev_daemon.sh` uses 7765/7766 and a separate dev config folder.
Do not run two daemons on the same port or against the same configuration.
Claude integrations use the bundled engine through `hooks/native.sh`.
Codex preview uses the explicitly configured endpoint; see `docs/codex.md`.

Before changing the live dev instance, read the stream handoff if supplied.
Always restart through `POST /shutdown` with `{"delay_seconds":60}`. Wait for
the port to free before relaunching; respect cancellation and postponement.
Never kill the daemon. Verify the microphone after restarting.

## Checks

Run `uv run pytest tests/unit tests/harness -q` for Python changes. Run dashboard
checks/build for frontend changes. Any component behavior change must update
its Storybook scenarios in the same commit. Use focused, meaningful tests.
Frozen integrations also have a real protocol smoke check in the release job.

## Releases

Use `scripts/bump_version.py` to keep all version files consistent. The native
release workflow builds, signs, notarizes and smoke-tests the app. Publication
requires explicit authorization. Update app and plugin together and verify the
running version and a spoken round trip. See `.claude/skills/creating-releases/SKILL.md`.

Keep changes in small functional commits. Never display credentials, private
configuration, or process command lines while on stream.
