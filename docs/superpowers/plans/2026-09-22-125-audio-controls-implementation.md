# Audio controls and provider capabilities implementation plan

**Goal:** Ship the approved configurable compact audio panel, then expose model-specific capabilities without redesigning capability-driven Settings yet.

**Architecture:** One shared AudioControls component renders dashboard or Settings rows. Visibility is a browser preference, independent of daemon audio values. Settings navigation explicitly selects Audio and focuses the controls section. Providers own typed language/streaming/smart-turn metadata; the daemon exposes selected-provider capabilities alongside existing compatibility fields.

## Part 1 — approved controls
- [x] Extract shared control definitions and component; retain one-click binary choices.
- [x] Default visibility: Microphone, Language, Turn detection. Persist explicit empty selection; hidden values stay untouched.
- [x] Replace dashboard controls; mount the same component in Settings Audio and implement direct navigation.
- [x] Expand end silence to 0–10000ms with requested choices; check actual VAD boundary behavior.
- [x] Promote Lab prototype to component stories; focused component/navigation/persistence tests, type check, dashboard/Storybook builds, visual check, commit.

## Part 2 — provider contract
- [x] Trace Grok/local provider and model behavior and verify official provider documentation.
- [x] Add typed metadata for supported languages (including unknown/voice-dependent), auto detection, streaming, smart turn; distinguish local turn detection from provider turn-end support.
- [x] Expose active direction/model metadata with backward-compatible existing flags.
- [x] Test at the provider boundary and API serialization, run relevant regression checks, commit.
- [x] Roll out with graceful delayed restart if required, verify microphone and state, push completed work. Leave capability-driven Settings changes for follow-up.

Do not touch unrelated hook edits or the untracked credential maintenance script. No model downloads or real provider calls needed for routine tests.

## Verification

337 dashboard tests; 481 Python unit/harness tests passed, one skipped; 12 focused contract/state-stream checks passed after final edits. Dashboard and Storybook builds passed. Shared control UI visually checked. Dev restarted gracefully using the preserved dev store; selected microphone remained Jabra Link 380. Active `/status` reports capability version 1 and local silence bounds 0–10000ms. Provider-driven Settings filtering and explanatory language UI remain deferred as requested.
