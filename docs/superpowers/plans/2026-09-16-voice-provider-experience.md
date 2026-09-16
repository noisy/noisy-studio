# Voice provider experience implementation plan

Execution: inline, authorized by the owner; no additional design checkpoints.

Goal: understandable speech settings with safe switching and provider-aware voices.
Architecture: retain provider protocols and playback queue; put selection policy and metadata in providers/, with a task-oriented Vue settings view.
Stack: Python, Vue 3, pytest, Vitest, Storybook.

## Constraints

Preserve existing choices and recordings. Never change the running daemon during tests. Work on codex/voice-provider-redesign. Commit functional increments locally. No publishing requested. Model capabilities are facts; quality and latency recommendations require measurements.

## 1. Provider request and replay isolation

Files: listener/speech.py, listener/audio_cache.py, providers/grok.py, providers/local.py; tests/unit/test_audio_cache.py and test_speech_pipeline.py.

- [ ] Fingerprint provider/model options in replay keys; retain actual audio format on replay.
- [ ] Freeze local options per provider instance; move xAI emphasis formatting into Grok adapter.
- [ ] Test cache separation and WAV replay alongside existing queue/retry tests.
- [ ] Run PYTHONPATH=src python -m pytest tests/unit/test_audio_cache.py tests/unit/test_speech_pipeline.py tests/unit/test_providers.py; commit passing increment.

## 2. Selection and voice catalog

Files: providers/config.py, providers/manifest.py, new providers/selection.py; listener/http_api.py; provider unit tests.

- [ ] Add direction-specific readiness, validated draft preparation and atomic apply. Preserve active configuration on failure.
- [ ] Add per-provider voice bindings, distinct suggestions, and reversible switching.
- [ ] Expose capabilities, model choices and voices without loading weights merely to list them.
- [ ] Test rejected configurations, missing dependencies, incomplete downloads and independent directions; commit.

## 3. Settings and Storybook

Files: new SpeechSettings.vue and stories/tests; SettingsView.vue; api/client.ts; daemon.fixture.ts; VoiceSelector.vue.

- [ ] Replace toggle diagram with Your speech / Agent voices cards and explicit draft/cancel/apply.
- [ ] Display live/batch behavior, local preparation and errors; explain models without backend jargon.
- [ ] Add candidate voice preview and assignment review; keep recognizable agent identity separate from engine voice ID.
- [ ] Test cancel, successful apply and failed apply; verify laptop rendering in Storybook and dashboard build; commit.

## 4. Research and measured evaluation

Inputs: GitHub #36, #46, #48, #70, #84, #86, #94; official model repositories.

- [ ] Verify viewer suggestions: Nemotron streaming, Canary 180M, Parakeet v3, Qwen3 ASR; distinguish language-inappropriate GigaAM/Moonshine uk variants.
- [ ] Reuse existing benchmark/corpus where possible; isolate model loading from the live daemon.
- [ ] Record actual local timings and accuracy where runtimes/assets are available; clearly report any untested candidates and reasons.
- [ ] Run relevant regression checks and retain a concise implementation/research handoff with outstanding limitations.
