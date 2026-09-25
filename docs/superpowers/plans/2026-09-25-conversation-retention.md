# Conversation history retention

Implement issue #157 with independently bounded conversation histories (200 cards each), and 100 shared system rows. Preserve existing mutable-card operations through a collection owned by ListenerState. Persist a versioned object keyed by conversation in the existing history.json, using atomic replacement; read legacy lists without dropping surviving rows. Persist trim counts and the global ID sequence. Display a concise trimmed-history notice in the conversation pane.

A larger disk archive and lazy loading are deliberately deferred: current WebSocket snapshots include all conversations and state recovery mutates their cards. Memory remains bounded per conversation, not globally. Already evicted legacy messages cannot be reconstructed. Closing a tab is not a history-clear operation; existing clear-history functionality does not exist.

- [ ] Implement isolated retention and migration with restart/regression tests.
- [ ] Add status metadata and trimmed-history component/story/test.
- [ ] Run focused and broader checks; commit functional increments.
