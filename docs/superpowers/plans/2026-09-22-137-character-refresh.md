# Character refresh implementation plan

Goal: fix #137 so voice/portrait changes update immediately and synchronize across windows.
Architecture: the shared daemon-state composable owns character changes, optimistic projection, serialized per-conversation saves, confirmation and rollback. Status snapshots carry canonical per-conversation characters for both WebSocket and polling paths. Character reads and saves cannot repaint another selected conversation. VoicePersona shows pending/error feedback; no automatic audio sample.

- [ ] Use typed saved /character response and snapshot character data.
- [ ] Own optimistic changes and ordered saves in shared state; protect against stale reads and tab switches; report errors.
- [ ] Add pending/failure presentation and Storybook states.
- [ ] Verify immediate update, external changes, failure rollback, ordered edits and tab races; run dashboard/Python checks and build.
- [ ] Commit, roll into dev with preserved data directory and countdown, push and resolve issue after verification.
