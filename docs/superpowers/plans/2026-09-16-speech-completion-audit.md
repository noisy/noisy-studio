# Speech redesign completion audit

The goal remains active. Earlier plan checkboxes describe implemented increments, not proof that the entire approved spec is complete.

## Verified increments

- Separate recognition and synthesis choices with explicit prepare/apply/cancel.
- Voice assignment review, cache isolation and format preservation.
- Local options captured per request; direction-specific dependency checks.
- Settings interaction tests, Python unit suite, dashboard build and rendered Storybook review.
- Initial reproducible Whisper/Nemotron experiments on existing human recordings.
- Download progress UI, including unknown totals and visibility after closing the editor.

## Remaining acceptance work

- Provider lifecycle now delegates through EngineAdapter, with a backend third-provider apply/bindings test. Further review must cover runtime registration and the remaining identity label compatibility path.
- Legacy macOS speech is restored in the catalog and covered by a shared-voice Storybook state and backend preservation test.
- Effective recognition mode is now reported by the status API and shown in the dashboard; provider capability combinations are tested. Review remaining mode selectors for clarity.
- Real cached Kokoro synthesis and isolated HTTP prepare/apply/preview now pass (tools/voice-evaluation). Browser microphone capture, streamed cloud output and failure recovery still need end-to-end coverage.
- Preparation now reports busy rejection explicitly and handles already-ready/in-progress requests idempotently; tested.
- Expand Storybook coverage for mixed/active local, voice sharing, unsupported language and actual preparation transitions.
- Benchmark coverage remains preliminary. The approved measurement matrix (Polish, identifiers, interruptions, cold/warm memory and actual conversational timing) is not satisfied by the current English batch transcription experiment. Report these gaps explicitly rather than implying a general model recommendation.
- Audit all original acceptance requirements against current code and test coverage before marking the goal complete.
