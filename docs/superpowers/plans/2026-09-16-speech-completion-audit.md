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

- Provider-neutral configuration metadata: selection.py still branches on Grok/local and synthesizes IDs. A frontend third-provider fixture alone does not prove backend extensibility.
- Preserve and expose legacy macOS speech selections through the same catalog; currently they remain executable but cannot be chosen in the new UI.
- Confirm active runtime capability reporting outside settings. Configured Live mode must not imply streaming for a batch-only engine.
- Exercise setup/test/apply against isolated real provider runtime, including audio formats, readiness and recovery; existing UI tests mock preview I/O.
- Review download scheduling: a second preparation request can currently be rejected silently by the global prefetch guard. Preparation must return accurate accepted/busy state.
- Expand Storybook coverage for mixed/active local, voice sharing, unsupported language and actual preparation transitions.
- Benchmark coverage remains preliminary. The approved measurement matrix (Polish, identifiers, interruptions, cold/warm memory and actual conversational timing) is not satisfied by the current English batch transcription experiment. Report these gaps explicitly rather than implying a general model recommendation.
- Audit all original acceptance requirements against current code and test coverage before marking the goal complete.
