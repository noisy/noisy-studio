# Agent-harness contract - implementation plan

Spec: `docs/superpowers/specs/2026-09-10-agent-harness-contract-design.md`.
Analysis: `docs/agent-integration-analysis.md`. Baseline tag:
`v3.0-pre-overhaul`. Rules: one phase at a time, each phase ends in a
green test run and one local commit; nothing is pushed.

## Phase 1 - the contract, no daemon changes
- `src/noisy_studio/harness/base.py`, `__init__.py` (REGISTRY),
  `claude_hooks/adapter.py`, `codex_hooks/adapter.py`, `fake/adapter.py`.
- Fixtures: `tests/fixtures/harness/claude-hooks/*.jsonl` from the
  2026-09-10 experiment; `codex-hooks/*.jsonl` synthesised from the
  existing Codex tests.
- `tests/harness/test_contract.py` - seven invariants x every registry
  entry. Green = a harness is "supported".
- Commit: "Agent-harness contract: adapters for Claude and Codex hooks".

## Phase 2 - ConversationRegistry, in-process
- `src/noisy_studio/listener/conversations.py` with alias table, order,
  listener lease, status, persistence (injectable clock and path).
- `tests/harness/test_conversations.py` - the ten scenarios via
  `FakeSession`.
- Commit: "Conversation registry: keys, aliases, listener lease".

## Phase 3 - wire the daemon
- `/harness/event`, `/harness/listener`, `/drain?conversation&listener`,
  `/speak` resolution through the registry, `/status.conversations`,
  registry persistence at boot; `state.py` agent strings = keys.
- `tests/integration/test_daemon_harness.py`.
- Commit: "Daemon routes speech and tabs through the harness contract".

## Phase 4 - thin hook scripts + install
- `hooks/claude_hook.py`, `hooks/codex_hook.py`, `hooks/_client.py`;
  `hooks/hooks.json`, `hooks/install.py`, `.claude/settings.json` (dev):
  add SessionStart/SubagentStart/SubagentStop, timeouts from
  `max_idle_seconds`.
- MCP server: identity required, cwd map and AGENT_NAME removed.
- `tests/integration/test_hook_scripts.py`; delete superseded unit tests.
- Commit: "Hooks become thin clients of /harness/event".

## Phase 5 - dashboard: listening state and tab order
- Storybook story for the `deaf` tab state with the "what to do" line;
  tabs read `/status.conversations`; new tabs append right.
- Commit: "Dashboard shows when an agent cannot hear".

## Phase 6 - remove the obsolete
- `hooks/exec.sh`, `hooks/mcp_exec.sh`, Docker hook registration paths,
  `sessions.json` writers/readers, `NOISY_STUDIO_CONFIG_DIR` special
  cases that only served dev-vs-prod, `docs/hooks.md` rewrite.
- Commit: "Drop Docker hook plumbing and cwd-based identity".

## Pending inputs
- Hook `timeout` cap experiment (running since 12:01): decides the default
  `max_idle_seconds` for `claude-hooks` - if no cap, 86400; if capped, the
  cap minus slack, and the `deaf` state carries the weight.

## Status (2026-09-10, end of session)

- Phase 1 DONE (dce7891) - contract + adapters + fixtures + invariant suite.
- Phase 2 DONE (a09f919) - ConversationRegistry + ten scenarios.
- Phase 3 DONE (b143594) - daemon /harness/event, alias resolution, listener
  lease, /status.conversations, receipts.
- Phase 4 DONE (315af7c) - thin hook scripts, MCP server carries no identity;
  legacy scripts later restored intact (097c498) because the native app runs
  them from this checkout - see docs/production-hooks-run-from-dev-checkout.md.
- U1 resolved (2bba3fc, f0ea37b) - no platform hook cap; Claude idle window
  raised to 4h, deaf state is the fallback.
- Phase 5 PARTIAL (5ca712c) - four Storybook proposals for the deaf tab
  state; wiring into AgentTabs.vue awaits Krzysztof's pick (Storybook-first).
- Phase 6 PENDING (deliberate) - removing Docker/`exec.sh`/`mcp_exec.sh`
  plumbing and giving the native app a frozen hook copy is high-consequence
  packaging work, entangled with how the app ships; do it with Krzysztof,
  not blind. The production-hooks flaw above is the first task of this phase.

## Restart note

A Claude session in this repo that was running before phase 4 loaded the
old hook config; the new `.claude/settings.json` (claude_hook.py) takes
effect on the next start. Restart Claude here once to pick it up.
