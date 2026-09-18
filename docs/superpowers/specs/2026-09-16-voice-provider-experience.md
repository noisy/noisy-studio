# Speech settings: provider experience redesign

Status: implemented and regression-tested; broader empirical validation remains incomplete. See the completion audit in ../plans/2026-09-16-speech-completion-audit.md.
Date: 2026-09-16. Baseline: origin/v3-desktop, 789fe39 (v3.0.0-alpha.9).
Worktree: noisy-coding-provider-experience. Branch: codex/voice-provider-redesign.

## Product decision

Make two independent choices understandable: how the app understands **your speech**, and how it produces **agent voices**. Prioritize accuracy, naturalness, and conversational responsiveness. Running locally is a useful option, not an automatic recommendation or a synonym for fast.

Keep existing users' selections. No automatic switch to a new service, no new cloud account requirement, and no silent network fallback for a local selection. OpenAI is an extension target; the first implementation need not integrate another service or download additional model families.

## Evidence from this codebase

These are code-review findings, not reproduced runtime failures or new benchmarks.

| Location | Current behavior | Consequence |
| --- | --- | --- |
| dashboard/src/components/SignalPath.vue | Buttons flip between two hardcoded provider IDs and save immediately. Technical local options remain separate from the selection. | More providers cannot fit this interaction; users cannot compare before changing. |
| Same component | Claims local recognition is faster than real time and replies take approximately five seconds on this machine. | Historical measurements are presented as current, universal product guidance. |
| providers/manifest.py | Local readiness combines recognition and synthesis dependencies. | A direction can look unavailable because the other direction needs a dependency. |
| listener/http_api.py, POST /providers | Saves selection before downloading models; accepts local options as an unrestricted dictionary. | A successful save is not a usable setup; unsuitable options can persist. |
| providers/local.py | Unknown requested voices resolve to a single configured Kokoro voice or af_sarah; macOS say also uses one global voice. | Agents can lose their distinct sound after switching. |
| dashboard/src/components/VoiceSelector.vue | Uses the static characterMath voice list. | The picker does not describe the active engine's actual voices. |
| listener/audio_cache.py | Fingerprint omits provider/model; cached bytes are always described as MP3. Local synthesis returns WAV. | A provider change can reuse an old provider's audio or return incorrect format metadata. |
| listener/speech.py | Converts emphasis into xAI loud tags before calling any provider. | Another engine may speak markup or interpret it differently. |
| providers/__init__.py | Unknown provider names fall back to Grok. | Invalid configuration can silently change the processing location. |
| listener/speech.py | Prepared speech already retains its provider instance. | Preserve this useful boundary; extend it to resolved model/options/voice rather than replace the queue. |

## Approaches considered

1. **One Cloud / Local preset.** Shortest setup, but obscures language support, voice changes, and useful mixed configurations. Rejected as the main settings model.
2. **Two task-oriented sections, with an inline choice panel. Recommended.** Explains the two decisions directly and keeps independent setup/test/apply operations. More providers become additional choices, not new forms throughout the app.
3. **A provider marketplace and detailed comparison table.** Useful for research, but too much terminology and maintenance for ordinary settings. Keep detailed comparisons in development documentation.

## Proposed screen

Place **Speech** in Settings, beside Appearance and Hotkeys. Move speech-provider configuration out of System; System retains unrelated diagnostics. Reuse existing dark surfaces, typography, user teal and agent periwinkle tokens.

Two vertically stacked sections avoid squeezing voice controls at laptop width. Each has a compact summary on the left and a contextual test on the right; narrow windows stack the test below. Only the section being changed expands.

    Speech
    Choose how you speak to your agents and how they reply.

    Your speech                         Try a sentence
    Grok · Online                       [Start microphone test]
    Text appears while you speak.       Live transcript and final result
    [Change]

    Agent voices                        Hear a reply
    Grok · Online                       [Choose agent] [Play sample]
    Your current voice assignments      Uses this agent's current voice
    [Change]

Expanded choices show provider/model name, Online / On this Mac, relevant language support, readiness, and the conversational behavior. An unavailable engine explains how to make it usable. No hidden click-to-cycle interaction. No price-first badges, invented quality stars, or fixed latency estimates.

Choosing a candidate edits a draft. Actions follow readiness: **Set up**, **Download**, **Try**, then **Use for my speech** or **Use for agent voices**. Cancel discards the draft. Preparing a candidate leaves the working selection active. Previews must explicitly identify the candidate, not misleadingly play the active engine.

Local recognition exposes a friendly model name with its actual technical name in secondary text. Initially retain the existing model choices, explained as tradeoffs; do not rename tiny/base into unsupported promises like “best quality”. Recommend one only after measuring it on target hardware. Hide compute type, threads, raw voice IDs and transport parameters from the ordinary flow. Advanced details are read-only unless an option has a supported use case and validation.

A batch-only recognizer says **Text appears after you finish speaking**. A streaming recognizer says **Text appears while you speak**. Streaming capability is separate from a speed rating. Unsupported existing Live controls show the effective behavior and a reason; preserve the user's preference for returning to a capable engine.

The microphone test records only after an explicit button press, stops before normal conversation resumes, and does not submit its transcript to a coding agent. TTS samples use the existing playback/cancellation path and stop on exit. Use a short, fixed sample with a coding term, a number, and a question. Never run paid previews automatically when browsing choices.

## Switching agent voices

Changing recognition never changes agent voices. Changing synthesis opens an inline **Review voices** step before Apply:

    Claude     Lux (Grok)      → Sarah (Kokoro)   [Listen] [Change]
    Codex      Rex (Grok)      → Adam (Kokoro)    [Listen] [Change]

Names above illustrate the UI only; no claim that these voices sound equivalent.

Remember assignments separately per provider/model voice catalog. Returning to Grok restores Lux/Rex rather than overwriting them with Kokoro IDs. Preselect deterministic distinct voices where possible, but show them as suggestions. If there are fewer compatible voices than agents, clearly show the shared assignments; never silently collapse all agents onto one fallback. Filter by the requested language before counting usable voices. A missing voice requires an explicit replacement or retention of the working provider.

Keep agent ID, character settings, and avatar identity independent of the provider voice reference. Preserve existing portraits on migration; don't label a different sound as Lux. Display agent name and current provider voice separately. New/unmapped voices use the existing neutral avatar fallback; artwork for every provider is outside scope.

## Narrow architecture changes

Extend the existing providers package rather than introduce a plugin framework or rewrite listener orchestration.

- **Catalog:** describe an engine per direction, with provider/model ID, location, languages, batch/live capability, configurable speed bounds, voice catalog reference and setup requirements. Backend owns capabilities; frontend consumes them. Readiness is per engine, not per company.
- **Readiness:** distinguish setup required, download required, downloading, loading/checking, ready, and failed. Unknown size is indeterminate progress. Credentials present is not equivalent to a successful connection. Do not load model weights just to list voices.
- **Selection service:** validate a draft, prepare the requested direction only, verify readiness and voice mappings, then atomically save. Reject stale draft revisions. Preserve last working selection if setup fails. Surface an error rather than replacing unknown providers with Grok.
- **Request snapshot:** at the start of an input turn or speech render, resolve immutable provider/model/options/voice/format. In-flight work finishes with that snapshot. A new selection affects subsequent turns/renders; already prepared audio keeps its identity. Existing stop/interruption controls remain in charge.
- **Voice bindings:** introduce a provider-qualified voice reference and persisted per-agent bindings at the provider boundary. Migrate legacy voice strings to Grok bindings without changing agent IDs or prompts. Adapt voice picker, allocation and voice-change endpoint to this catalog; avoid rewriting conversation storage.
- **Cache:** include provider, model and relevant synthesis configuration in fingerprints, and retain content type with bytes. Version the cache namespace so legacy entries do not collide. Preserve replay behavior, bounded eviction and the existing playback queue.
- **Adapter formatting:** pass plain text/intended emphasis at the common boundary. xAI-specific markup belongs in its adapter. An engine without emphasis support receives readable text. Speed controls use capability bounds; never silently claim a requested unsupported rate was applied.
- **Usage:** distinguish provider-reported usage from estimates. The current per-character estimator can remain for Grok; don't present a token-priced provider's character estimate as an actual charge. This need not become a billing-system rewrite.

Keep the existing /providers route and legacy active IDs during migration; add structured engine selections and readiness data additively. Centralize validation so old callers cannot bypass readiness. Version persisted configuration and keep a backup before migration. Credentials continue through the existing credential storage boundary, never a new frontend JSON settings field. No arbitrary user-supplied shell commands or model install paths.

Touch points are providers/, provider routes, speech/cache adaptation, voice allocation/picker, and Settings. Website and companion remain consumers of existing agent state; they should not branch on provider names. Additive state fields must not invalidate recorded website fixtures.

## Research shortlist and what it establishes

Primary sources checked on 2026-09-16. These are documented capabilities and candidates, not independent performance rankings. Catalog contents and model availability must be verified again when implementing an adapter.

| Candidate | Documented facts | Decision |
| --- | --- | --- |
| Grok STT/TTS | Existing adapters; documented partial/final recognition events and voice listing. | Keep as the working baseline. Measure actual network and playback latency. [STT](https://docs.x.ai/developers/model-capabilities/audio/speech-to-text), [TTS](https://docs.x.ai/developers/model-capabilities/audio/text-to-speech). |
| OpenAI Speech + live transcription | Speech supports streamed output and model-dependent voices; current guide lists 13 for the newer TTS offering. Live transcription exposes incremental and final events with item IDs; current guide recommends gpt-live-transcribe. | Design independent input/output adapters. Normalize deltas to the app's transcript semantics and resample in the adapter. Do not substitute a speech-to-speech assistant for Claude/Codex. [Speech](https://developers.openai.com/api/docs/guides/text-to-speech), [live transcription](https://developers.openai.com/api/docs/guides/realtime-transcription). |
| faster-whisper | Existing local recognizer. Upstream throughput benchmarks vary by hardware, precision and batching. | Keep as baseline. Upstream long-file throughput does not establish this app's interactive delay. [Repository](https://github.com/SYSTRAN/faster-whisper). |
| WhisperKit | Apple-focused runtime with model selection and microphone streaming; upstream recommends larger Turbo variants for production quality and describes tiny as a development option. | Strong candidate for an isolated Mac recognition experiment, not a guaranteed improvement. Native integration/distribution cost matters. [Repository](https://github.com/argmaxinc/argmax-oss-swift). |
| Parakeet TDT 0.6B v3 | Multilingual recognition model; 600M parameters and 16 kHz mono input. | Secondary local recognition candidate; validate Mac runtime/distribution and relevant language accuracy before adding UI options. [Model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3). |
| Kokoro 82M | Existing local synthesis family, with multilingual upstream implementation and voice packs. Our current adapter exposes only a subset and ignores the requested language in its model call. | Fix honest capability reporting and voice assignment before advertising broader support. [Model](https://huggingface.co/hexgrad/Kokoro-82M), [implementation](https://github.com/hexgrad/kokoro). |
| Qwen3-TTS | Released 0.6B/1.7B variants; documented streaming, preset voices and optional voice design/cloning. Listed languages do not include Polish. | Research candidate only. Published streaming claims do not establish first-audio latency on this Mac; larger packaging/runtime work is outside the first redesign. [Repository](https://github.com/QwenLM/Qwen3-TTS). |

Do not add every researched model to the application. First compare existing Grok and local engines, then one promising Mac recognizer. Keep OpenAI's contract ready without showing a selectable service that has no working adapter.

## Measurement plan

The existing tools/bench_voice.py is useful for a smoke baseline, but uses synthetic speech and a few timings. It cannot settle accent accuracy or conversational quality.

Use an isolated benchmark process and explicit configurations; never change the live daemon's provider selections. Reuse a curated subset of our authorized demo recordings, preserving originals. Add English with a Polish accent, Polish, mixed English coding terms, filenames, numbers, short commands, long requests, pauses, and background noise. Store references and corrections locally in the benchmark corpus; cloud transmission is explicit per run, not automatic on settings open.

For each tested configuration record model/runtime versions, hardware, input duration, language, cold load separately, and at least 20 warm repetitions of the timing subset. Report median and p95, with the sample count and failures. Alternate cloud/local runs rather than run all cloud requests during a different network period.

- Recognition: end-of-speech to final transcript, first useful partial, overwritten/dropped words, word error rate, and exact correctness of important identifiers. Include turn detection delay rather than hiding it in the model benchmark.
- Synthesis: request to first audible output, completion time, stalls, interruption response and queue behavior. Listen blind to naturalness, pronunciation and distinguishability across agents. Evaluate the playback path used in the product, not just downloaded file time.
- Local usability: cold start, installed size, peak memory, sustained responsiveness while a coding agent is active, offline success and recovery from incomplete downloads.
- Recommend a default only after user listening review and recorded measurements. No hard speed promise in UI from a single computer or vendor benchmark. Unmeasured candidates stay labeled untested in developer reports, not ranked in settings.

## Delivery boundaries and acceptance

After design approval, prepare a concrete implementation plan and deliver small tested commits:

1. Contract and migration/cache corrections with existing providers; no new model downloads or default changes.
2. Settings and Storybook: active cloud, mixed setup, local unavailable/downloading/error/ready, candidate test, voice replacement, insufficient voices, unsupported language and small viewport.
3. Wire prepare/test/apply and provider-aware voice assignments; verify unchanged Grok behavior, local behavior and switching back.
4. Run isolated comparisons, publish measured findings, and decide whether a new local runtime is justified as a separate increment.

Acceptance includes: failed setup cannot disable working speech; cancelled drafts do not alter settings; returning to a provider restores voices; per-direction preparation doesn't download the other engine; cache never reuses another engine's synthesis; WAV/MP3 replay works; malformed options fail clearly; streaming transcript deltas cannot erase finalized turns; voice previews stop correctly; keyboard navigation and screen-reader labels work; Storybook screenshots at laptop and narrow widths contain no clipped controls. A fake third-provider fixture must render through the same settings components, demonstrating extensibility without claiming OpenAI is implemented.

Deferred: automatic model ranking, installing arbitrary runtimes, voice cloning, managed billing, per-agent model selection, a wholesale audio-transport rewrite, and changes to website branding or synthetic demos.

## Review decision

Implemented direction: two task-oriented sections with draft/test/apply and explicit voice reassignment. Model quality rankings remain an empirical follow-up, not an assumption embedded in this proposal.
