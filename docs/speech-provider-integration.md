# Adding a speech engine

The Settings → Speech screen consumes backend metadata; it does not know provider names. Recognition and synthesis are independent selections. Existing Grok and local selections remain the defaults for their current users.

## Extension points

1. Implement the applicable `STTProvider` / `TTSProvider` protocol in `src/noisy_studio/providers/base.py`. Constructors capture provider options without loading weights. Capture voice bindings and include synthesis-relevant options in `cache_identity`; preserve the returned audio content type. Translate provider failures into `STTError` / `TTSError`.
2. Add lazy factories to `_STT_FACTORIES` / `_TTS_FACTORIES` in `providers/__init__.py`. Options are read from that provider's namespace. Local retains its legacy file location for compatibility.
3. Register an `EngineAdapter` in `providers/engine_registry.py`. Supply choices, draft options, readiness, voices, preparation, active choice and language validation. Optional `active_voice_labels` handles legacy runtime mapping; otherwise labels use the saved voice bindings. Catalog construction must not download or load models.
4. Add credential/setup support to the existing provider manifest and credential store if needed. A choice may declare `setup_action: "system-settings"` only when that screen can resolve its setup requirement. Never include credentials in catalog responses or cache identities.

Stable choice IDs distinguish models with different catalogs. `voice_bindings_by_engine` retains each model's assignments. Agent identities and portraits are separate from native voice IDs. The active labels shown in settings come from runtime resolution, not suggested replacement assignments.

## Runtime behavior

- Prepare downloads only the requested direction. It never activates a candidate.
- Apply validates readiness, language, complete voice mappings and the draft revision, then atomically saves the selected direction.
- Recordings capture recognition provider and language at their start. Queued/prepared speech retains its synthesis provider and format.
- Readiness controls capture; a local recognizer does not require cloud credentials.
- Live capability is distinct from user preference and playback transport. Browser output currently uses complete clips even for a streaming-capable provider.
- Failed or cancelled previews must not enqueue conversation messages. A delayed microphone permission/status response must not restart a cancelled test.

The fake third-provider tests cover metadata/apply and runtime option isolation separately. The Storybook Third Provider state verifies generic rendering. OpenAI is not implemented or advertised as selectable by this change; its eventual adapter must use the same boundaries, with provider-specific streaming event handling and its real voice catalog.

See `tools/voice-evaluation/README.md` for measured local results and their limits. Do not infer relative quality or promise speed from catalog names, model sizes, or vendor claims.
