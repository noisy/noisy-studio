# Codex Integration Implementation Plan

**Goal:** Package working Codex voice support and display actual agent names.

**Architecture:** Reuse the daemon and hook scripts. A Codex adapter supplies
identity per MCP call and loads one endpoint configuration for both directions.

**Tech Stack:** Python, pytest, stdio MCP, Codex plugin JSON, Vue/Vitest.

## Global constraints

- Base: `v3-desktop` at `0a53f50`; isolated `feat/codex-integration`.
- No live configuration changes, daemon restarts, releases, or merges.
- No OpenAI voice provider or queue bridge.
- Preserve Claude identity behavior when `agent_id` is omitted.
- Preserve unrelated user configuration; never manufacture hook trust.

### Task 1: Per-call identity and shared lifecycle adapter

Files: `src/noisy_studio/server.py`, `hooks/codex.py`,
`hooks/_codex_config.py`, `hooks/_agent_identity.py`,
`tests/unit/test_codex_hooks.py`, `tests/unit/test_server_identity.py`.

- [x] Test an interleaved shared MCP client using explicit identities and
  an omitted identity; inspect request bodies, including absence of fallback.
  Contract: `await speak(text, agent_id="session-a")` posts
  `{"text": text, "interrupt": False, "wait": True, "agent": "session-a"}`.
- [x] Add `agent_id: str | None = None` to identity-sensitive tools. Explicit
  empty values return a visible error in the Codex launcher; legacy servers
  ignore supplied identity and retain their existing routing.
- [x] Test forged/missing identity. Adapter output for a speech tool contains
  `hookSpecificOutput.updatedInput.agent_id == hook_input["session_id"]`.
- [x] Implement a stdlib adapter dispatching to canonical hooks, selecting
  port before imports, suppressing cwd-map writes for Codex, and emitting
  both a warning and best-effort `/event` on identity failure.
- [x] Run `uv run pytest tests/unit/test_codex_hooks.py tests/unit/test_server_identity.py -q`.

### Task 2: Reversible plugin onboarding

Files: Codex manifest/MCP/hook configuration, `hooks/codex_mcp.py`,
`scripts/install_codex.py`, dedicated Codex skills, `tests/unit/test_codex_install.py`.

- [x] Build the plugin around canonical source paths; validate with real
  Codex CLI rather than relying on stale packaging assumptions.
- [x] Store only integration settings in a dedicated JSON file. Endpoint
  configuration feeds both the adapter and MCP launcher.
- [x] Installer CLI: `install_codex.py --port PORT [--listen-seconds N]`;
  remove with `--uninstall`. Do not replace hooks.json or config.toml.
- [x] Test repeat install, custom ports, existing unrelated files, invalid
  existing JSON, and removal. Run `uv run pytest tests/unit/test_codex_install.py -q`.
- [x] Test plugin add/remove in a temporary CODEX_HOME; validate skill and
  hook discovery without changing this session.

### Task 3: Agent-neutral display and documentation

Files: chat bubble/feed components, status labels, affected stories/tests,
`README.md`, `docs/INSTALL.md`, `docs/hooks.md`, `docs/codex.md`.

- [x] Use daemon `agent_labels` for display with an `Agent` fallback;
  preserve speaker overrides and daemon identity. Keep old history wire
  keys compatible; remove brand names from general user-facing copy.
- [x] Add rendering tests with arbitrary agent labels and old history.
  Update corresponding stories, then run `npm test -- --run` if supported,
  otherwise `npx vitest run`, followed by typecheck and build.
- [x] Document install, hook review, spoken round-trip, endpoint selection,
  one-hour Stop hold, shorter wait, removal, and platform prerequisites.
- [x] Run full Python unit suite, inspect diff, commit, and send supervisor
  evidence. Merge only after supervisor review.

## Research result

An isolated 0.153.4 app-server emitted `turn/started` after `codex queue`
targeted an idle thread. The queue became empty. No credentials were
provided, so model completion was intentionally not tested. Supervisor
approved keeping that bridge out of this implementation.


## Verification evidence

- Python: 199 tests passed (including three real subprocess/HTTP lifecycle
  tests), up from the 181-test baseline. Ruff passed on changed Python files.
- Dashboard: 180 tests passed; TypeScript/Vite production build passed.
- Dedicated skill passed the skill-creator validator.
- Codex CLI 0.153.4 installed a clean package in an isolated CODEX_HOME.
  Actual app-server discovery found all five hook definitions, left untrusted,
  and connected the MCP server with all five tools. The dedicated Codex skill
  was enabled. Codex also migrates the legacy setup command, now redirected
  to Codex instructions when running in Codex.
- Actual app-server MCP calls sent A/B/A to a local test HTTP endpoint with
  the correct identities and no cwd fallback. Missing identity reported an
  error event without sending speech. No provider/audio call was used.
- Packaged installer configured a custom endpoint and removed its settings.
  Plugin-relative `cwd` fixes MCP path resolution; `env_vars` explicitly
  forwards endpoint/config overrides through Codex's filtered environment.
- Real hook subprocesses delivered distinct transcripts to two sessions in
  one directory. Stop returned exit 2 plus speech on stderr. Disabled Stop
  cleared activity without draining; duplicate listeners reported their lock
  conflict and left the queue intact. Legacy Claude routing, including forged
  overrides, is covered by server regression tests.
- Claude hook JSON and manifest remain byte-identical to the base revision.
- A microphone/speaker round trip in a newly installed, trusted Codex session
  remains a manual acceptance check. Isolated checks prove packaging and
  routing, not audible playback or model consumption of trusted hook output.
