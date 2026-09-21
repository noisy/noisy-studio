# V3 clean technical rebrand implementation plan

Goal: independently rename current main and provide an explicit manual upgrade guide.
Approved revision: clean V3 break; remove the compatibility layer from the initial stage. No old aliases or automatic migration. Work inline; commit locally, do not push.

- [x] Inventory current main and PR #90; establish baseline tests. Record the user's revised clean-break decision in the spec.
- [x] Rename Python distribution/package, imports, metadata, entry points, executable and build consumers together. Remove the first-stage compatibility resolver. Synchronize/install and verify Python unit/harness contracts and frozen MCP/hook protocols.
- [x] Rename integration/env/config/profile/preference/OS identifiers and package manifests. Keep the live dev endpoint and data store explicitly selected; verify frontend and desktop checks/builds.
- [x] Update current docs, tools, skills, fixtures and links. Write the agent-friendly manual upgrade and rollback guide; audit all remaining old-name references.
- [ ] Verify packaged engine and actual dev UI/history/microphone/voice using postponed restart. Record release-only signed-upgrade and host-reconnection limits. Add PR #90 to local post-push follow-ups without publishing.

Commands: uv --no-config sync; NOISY_STUDIO_CONFIG_DIR=<isolated test directory> uv run --no-config pytest tests/unit tests/harness -q; dashboard npm test -- --run and npm run build; desktop npm test; uv --no-config build; PyInstaller desktop/daemon.spec; scripts/smoke_integrations.py with the renamed executable. Keep output logs in /tmp and do not print secrets or full private state.
