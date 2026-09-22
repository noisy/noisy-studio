# Harness payload fixtures

One directory per registry entry (`noisy_studio.harness.names()`), one
JSONL file per scenario, one raw hook payload per line, in the order the
agent system sent them. `tests/harness/test_contract.py` requires
`session.jsonl`, `resume.jsonl` and `title.jsonl`; `participant.jsonl`
(a subagent inside the session) is optional but expected wherever the
agent system has subagents.

- `claude-hooks/` - recorded 2026-09-10 from Claude Code 2.1.267 with
  `claude --bg` (see docs/agent-integration-analysis.md §10). Paths were
  shortened; ids are verbatim. The `mcp__noisy-studio__speak` PreToolUse
  row in `session.jsonl` and the `resume.jsonl` / `title.jsonl` files are
  synthesised from the recorded shape.
- `codex-hooks/` - synthesised from the shape asserted by the existing
  Codex tests (`tests/unit/test_codex_hooks.py`); replace with a recording
  when one exists.
- `grok-hooks/` - synthesised from Grok's hook reference (camelCase
  `sessionId` / `toolName` / `toolInput`, plus `hook_event_name`). Grok
  has no recorded fixture yet.
