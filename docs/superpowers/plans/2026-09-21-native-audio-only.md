# Native audio only (#99; PR #103 context)

Approved direction: remove browser capture/playback completely for V3. Keep native microphone selection, system speaker playback, PTT, playback controls, and live dashboard state updates. Do not publish or contact the contributor yet.

- [x] Extract the existing WebSocket state stream from the audio lease bridge, rejecting obsolete audio connections. Remove browser transport, leases, PCM ingestion and playback branching.
- [x] Normalize legacy browser microphone settings to the system microphone and remove legacy output selection when saving migrated settings. Native hardware failures stay native and retry without opening a browser capture path.
- [x] Remove dashboard audio activation, browser device choices, browser microphone/agent-playback Web Audio code, and obsolete tests/docs. Preserve native playback pause/skip and microphone levels.
- [ ] Verify native playback, failed-device recovery, legacy migration, state stream and UI; rebuild Storybook/native engine and roll into dev using the postponable restart. Commit locally on main, without pushing.
