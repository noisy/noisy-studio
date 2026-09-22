# Provider audio capabilities

`TTSProvider.capabilities` and `STTProvider.capabilities` return immutable `AudioCapabilities`. The active provider constructs metadata for its selected model/options without downloading weights, opening devices, or contacting an API. `/status` and pushed snapshots expose `audio_capabilities` version 1 with separate `stt` and `tts` entries. A missing/unconfigured direction is null. Existing streaming flags remain compatible.

Each direction reports provider, model, modes, languages, and optional smart_turn. Grok reports `service-default`: current clients do not pin a model, so metadata must not claim they do. Local Whisper metadata distinguishes English-only, standard multilingual, large-v3, and unknown custom models. Kokoro reflects this integration's English voices, not every language the upstream model might support. macOS `say` reports voice-dependent languages and no language override.

Language `codes: null` means unknown or dependent on the voice, not universal support. `exhaustive: false` means omission is not a rejection. `auto_detect: null` means unknown. `purpose` distinguishes recognition, formatting, synthesis, and voice selection. Codes use provider-native spelling; do not blindly intersect STT `pt` with TTS `pt-BR`. No whitelist enforcement or migration of saved language choices is introduced here.

Smart Turn metadata comes from the Grok STT provider and applies only in live mode. Its off_value describes Noisy Studio's existing convention: zero means omit the API parameter. Ordinary Auto/Push-to-talk and end-silence thresholds belong to Noisy Studio's local segmenter, so they are declared separately as application controls. The 0–10000ms local silence range is not xAI's endpointing range. Zero closes on the first quiet audio frame, never a voiced frame.

Follow-up UI work should use this contract to explain model/language differences and gate controls. This change does not redesign Settings based on capabilities or silently replace selected modes/languages.

Sources checked 2026-09-22:
- https://docs.x.ai/developers/model-capabilities/audio/speech-to-text — separate STT formatting codes, streaming and Smart Turn.
- https://docs.x.ai/developers/model-capabilities/audio/text-to-speech — documented TTS codes and additional languages with varying accuracy.
- https://github.com/openai/whisper/blob/main/whisper/tokenizer.py — language token ordering.
