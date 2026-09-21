"""Agent-harness registry - the daemon's single door to agent systems.

One entry per supported harness. The contract suite in
`tests/harness/test_contract.py` iterates over exactly this table, so a
new harness is one directory plus one line here, and it is not supported
until its fixtures make the suite green.
"""

from noisy_studio.harness.base import (
    Capabilities,
    Delivery,
    Event,
    Harness,
    HarnessError,
    Interpretation,
)

__all__ = [
    "Capabilities",
    "Delivery",
    "Event",
    "Harness",
    "HarnessError",
    "Interpretation",
    "get",
    "names",
]


def _claude_hooks() -> Harness:
    from noisy_studio.harness.claude_hooks.adapter import ClaudeHooks

    return ClaudeHooks()


def _codex_hooks() -> Harness:
    from noisy_studio.harness.codex_hooks.adapter import CodexHooks

    return CodexHooks()


REGISTRY = {"claude-hooks": _claude_hooks, "codex-hooks": _codex_hooks}


def names() -> list[str]:
    return sorted(REGISTRY)


def get(name: str) -> Harness:
    name = {"claude": "claude-hooks", "codex": "codex-hooks"}.get(name, name)
    if name not in REGISTRY:
        raise KeyError(f"unknown harness {name!r}; have {names()}")
    return REGISTRY[name]()
