"""The conversations the user settled, as the dashboard's Settled section shows them.

Settling hides a conversation (it leaves the agents table, stays in the
registry). The dashboard lists them so they can be restored, but the
registry keeps every conversation ever seen (hundreds on a dev machine), so
only the most recently active ones are sent, with the total for "+N older".
"""

from __future__ import annotations

from collections.abc import Container

from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.workspace import WorkspaceCache

SETTLED_LIMIT = 30


def settled_conversations(
    registry: ConversationRegistry,
    workspaces: WorkspaceCache,
    listed: Container[str],
    limit: int = SETTLED_LIMIT,
) -> dict:
    """{"total": every settled conversation, "items": the newest `limit` rows}.

    `listed` are the conversations already in the list (the agents table);
    a hidden one that is still there is shown once, as its own row."""
    keys = [key for key in registry.settled_keys() if key not in listed]
    return {"total": len(keys), "items": [_row(registry, workspaces, key) for key in keys[:limit]]}


def _row(registry: ConversationRegistry, workspaces: WorkspaceCache, key: str) -> dict:
    conversation = registry.get(key)
    assert conversation is not None  # settled_keys only names known conversations
    workspace = workspaces.get(conversation.cwd) if conversation.cwd else None
    return {
        "name": key,
        "label": conversation.label(),
        "project": workspace.project if workspace else None,
        "branch": workspace.branch if workspace else None,
        "last_active_at": conversation.last_event_at,
        "ended": conversation.ended,
        "talk_key": registry.talk_key(key) or None,
        "snoozed_until": registry.snoozed_until(key),
    }
