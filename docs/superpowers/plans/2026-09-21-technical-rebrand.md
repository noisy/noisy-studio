# Technical rebrand implementation plan

Approved design: ../specs/2026-09-21-technical-rebrand-design.md. Execute inline on main; no pushes or host configuration edits.

Goal: make noisy-studio canonical while preserving existing installations.
Architecture: one stdlib environment/config compatibility boundary, canonical package and tools, explicit old-name adapters. Existing persistent stores are reused in place; no live database moves or merging independent histories.

- [ ] Environment boundary: add environment.get(name, default), resolving new prefix first and legacy prefix second, preserving explicit empty values. Convert runtime and standalone hook readers. Test precedence and defaults; run unit/harness baseline and focused tests; commit.
- [ ] Package/build cutover: rename src/noisy_coding to src/noisy_studio; update imports, metadata, CLI/build paths, lockfiles and integration commands. Keep legacy CLI and package import aliases for running source sessions. Verify aliases resolve the same module objects, build/install and frozen MCP/hook protocols; commit.
- [ ] Persistence/integrations: canonical fresh config paths, reuse established stores without moving live databases, respect explicit overrides. Update hook ownership matching and Codex settings discovery; new environment names in launchers with legacy fallback. Migrate browser preferences once with canonical precedence. Keep OS app IDs. Test fresh/legacy/collision cases and installer idempotence; commit.
- [ ] Desktop and documentation: canonical engine filename, legacy installed-engine discovery, canonical fresh Electron profiles with old-profile reuse. Update package manifests/current docs/skills/URLs and enumerate remaining compatibility/historical references; run desktop/frontend checks and builds; commit.
- [ ] Rollout: frozen engine protocol smoke, full Python unit/harness and frontend suites, postponed dev restart only after replacement is ready. Verify isolated config, Jabra microphone, dashboard/state stream and voice. Record limits (signed macOS upgrade not proven by source tests). Add PR #90 to local post-push follow-ups; do not publish.

Check commands: uv run pytest tests/unit tests/harness -q; dashboard npm test -- --run and npm run build; desktop npm test; PyInstaller desktop/daemon.spec; uv run python scripts/smoke_integrations.py <new frozen engine>. Logs stay in /tmp; never print private configuration.
