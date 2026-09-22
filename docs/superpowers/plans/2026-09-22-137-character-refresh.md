# Character refresh implementation plan

Goal: fix #137 so voice/portrait changes update immediately and synchronize across windows.
Architecture: the shared daemon-state composable owns character changes, optimistic projection, serialized per-conversation saves, confirmation and rollback. Status snapshots carry canonical per-conversation characters for both WebSocket and polling paths. Character reads and saves cannot repaint another selected conversation. VoicePersona shows pending/error feedback; no automatic audio sample.

- [x] Use typed saved /character response and snapshot character data.
- [x] Own optimistic changes and ordered saves in shared state; protect against stale reads and tab switches; report errors.
- [x] Add pending/failure presentation and Storybook states.
- [x] Verify immediate update, external changes, failure rollback, ordered edits and tab races; run dashboard/Python checks and build.
- [x] Commit, roll into dev with preserved data directory and countdown, push and resolve issue after verification.

Validation: 320 dashboard tests passed; focused character/shared-state tests passed again after fixture typing correction. Ten relevant Python tests passed. Dashboard and Storybook builds passed; pending/failure previews rendered correctly. Dev restarted with the postponable 60-second countdown and preserved store; live HTTP and WebSocket character payloads match, and Jabra Link 380 remains selected. No automatic voice sample was added.
