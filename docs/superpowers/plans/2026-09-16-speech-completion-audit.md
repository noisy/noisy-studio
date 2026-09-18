# Speech redesign completion audit

Updated 2026-09-18. The feature is implemented in `codex/voice-provider-redesign`, with the validation limits below. Earlier plan checkboxes describe implementation increments, not completion of the entire research matrix. No push or merge has been performed.

## Verified behavior

| Requirement | Evidence |
| --- | --- |
| Separate recognition and synthesis; explicit prepare/apply/cancel | Selection tests, settings interaction tests, isolated HTTP prepare/apply run |
| Preparation preserves working selection; stale drafts rejected | `test_provider_selection.py`; first-run preparation now refreshes/polls on 409 and requires explicit apply |
| Download progress and failure recovery | Known/unknown totals in Storybook; incomplete downloads never published; retry tests |
| Local operation without a cloud key | Capture gates on selected STT readiness; real keyless Whisper + Kokoro HTTP setup verified |
| Per-turn engine and language snapshot | `RecognitionRequest` captured at recording start; batch and streaming-cost regression tests |
| Provider/model voice assignment preservation | Per-engine saved bindings; runtime voice labels are separate from suggested replacements |
| Provider-owned compatibility behavior | `EngineAdapter`; third-provider settings and runtime option-isolation tests; legacy macOS/Kokoro labels covered |
| Replay format and provider isolation | Existing speech/cache tests preserve WAV/MP3 type and configuration fingerprints |
| Cancelled previews cannot restart later | Microphone acquisition cleanup tests plus delayed status-check Cancel/unmount regression tests |
| Live capability versus actual behavior | Status uses the playback decision, including browser batch output and live override; settings shows effective mode |
| Late transcript updates cannot reopen finished turns | Finalized/cancelled turn tests at the state boundary |
| Setup and unsupported-language guidance | Missing-runtime guidance no longer points to unrelated credential settings; language mismatch blocks Apply |
| Responsive UI and onboarding | Rendered narrow/laptop Storybook inspection; new Preparing Before Apply story; earlier independent design review |

Independent follow-up review found and confirmed closure of microphone cancellation, current voice labels, live-mode wording, and onboarding preparation issues. It also identified the old API-key capture gate, now replaced. Capture/finalize snapshot paths were reviewed separately.

## Verification on 2026-09-18

- Full Python suite: **394 passed, 1 skipped**. After adding the changed-backup stale-request case, the affected provider-selection suite passed **22 tests**.
- Full dashboard suite: **291 passed, 44 files**.
- Dashboard production build and Storybook build passed. Storybook retains its existing large-chunk warning.
- Isolated HTTP test: real Kokoro WAV preview, no queued agent messages, keyless local readiness and selection confirmed.
- Cached Whisper offline test and earlier Kokoro synthesis experiments retained in `tools/voice-evaluation`.
- Deterministic synthetic-noise probe: 45 offline transcriptions across tiny/base/small and clean/20 dB/10 dB conditions; results and limitations retained in `tools/voice-evaluation/noise-results.json`.
- New isolated-process measurements record model snapshot sizes, peak process RSS, first inference and 20 warm repetitions per model.
- Storybook available on port 6013; no live daemon configuration changed.

## Validation still outstanding

- Real browser microphone permission/recording interaction and live cloud streaming/recovery have not been exercised end to end in this pass. Automated lifecycle and playback-boundary tests do not substitute for those hardware/network checks.
- The broad research matrix is incomplete: Polish-language speech, coding identifiers, real-world background noise, end-of-turn latency, concurrent coding workload, cloud comparisons and blind listening quality still need a suitable corpus/runs. Current human recordings are English with a Polish accent. Do not claim a general model-quality winner or change defaults from these results.
- Saved-settings corruption now fails closed without selecting an online fallback. The dashboard offers an explicit restore when a valid backup exists, preserves the damaged file, and rejects stale actions when either file changes. API/filesystem tests and the rendered Storybook recovery action verify this path. Without a valid backup, manual repair remains necessary; no defaults are silently written.
- Adding OpenAI still requires its runtime adapter, credentials integration and provider-specific streaming event handling. The redesign supplies extension boundaries; it does not implement OpenAI.

See `docs/speech-provider-integration.md` for the concrete extension points. These limits remain visible rather than treating green tests as proof of every original acceptance item.
