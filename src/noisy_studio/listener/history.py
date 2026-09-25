"""Conversation-local retention; callers hold ListenerState's lock."""

from collections import deque

CONVERSATION_HISTORY_SIZE = 200
SYSTEM_HISTORY_SIZE = 100


class ConversationHistory:
    def __init__(self) -> None:
        self._rows: dict[int, dict] = {}
        self._conversations: dict[str, deque[int]] = {}
        self._system: deque[int] = deque()
        self.trimmed: dict[str, int] = {}

    def __iter__(self):
        return iter(self._rows.values())

    def __reversed__(self):
        return reversed(self._rows.values())

    def append(self, row: dict) -> None:
        if row['id'] in self._rows:
            return
        system = row.get('role') == 'system'
        agent = str(row.get('agent') or '')
        bucket = self._system if system else self._conversations.setdefault(agent, deque())
        limit = SYSTEM_HISTORY_SIZE if system else CONVERSATION_HISTORY_SIZE
        self._rows[row['id']] = row
        bucket.append(row['id'])
        if len(bucket) > limit:
            del self._rows[bucket.popleft()]
            if not system:
                self.trimmed[agent] = self.trimmed.get(agent, 0) + 1

    def snapshot(self, sequence: int) -> dict:
        return {
            'version': 2,
            'sequence': sequence,
            'conversations': {
                agent: [dict(self._rows[row_id]) for row_id in rows]
                for agent, rows in self._conversations.items()
            },
            'system': [dict(self._rows[row_id]) for row_id in self._system],
            'trimmed': dict(self.trimmed),
        }
