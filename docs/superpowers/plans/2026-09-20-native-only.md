# Native-only distribution (#114)

Goal: the supported user installation is the macOS app, with integrations
connected to its engine on 9765. Development remains isolated on 7765.

The current Claude MCP launcher still depends on the retired deployment path.
Replace it with hooks/native.sh, which finds the installed app's engine in
/Applications or ~/Applications (or an explicit developer override). The frozen
engine gains separate MCP and Claude-hook entry modes; neither starts audio or
an extra daemon. Hooks retain their exit-code/stdout/stderr delivery contract.
The standalone Codex preview integration keeps its explicit uv prerequisite and
configured endpoint; do not overwrite local integration settings.

- [ ] Replace obsolete launchers and manifest targets; test missing app,
      explicit engine/port, protocol output and hook exit-code preservation.
- [ ] Remove retired image-build, compose and registry artifacts; update current
      runtime branches and documentation to the supported native installation.
- [ ] Verify unit/harness, frontend, desktop and build checks. Freeze the engine
      and verify a real MCP initialization/tool listing plus hook execution.
- [ ] Commit coherent increments; restart dev only if its runtime changes require
      it, using the 60-second postponable countdown and microphone checks.

Historical references deliberately retained (list these in a future PR):
- docs/agent-integration-analysis.md — dated pre-overhaul analysis, marked historical.
- docs/superpowers/specs/2026-09-05-codex-integration-design.md
- docs/superpowers/specs/2026-09-10-agent-harness-contract-design.md
- docs/superpowers/plans/2026-09-10-agent-harness-contract.md

Current guides, code, manifests and workflows must not retain instructions for
the retired distribution. No installed application or private configuration is
removed as part of repository cleanup. Signing and release publication remain
separate actions; this task does not publish a new app.
