# Speech engine evaluation — 2026-09-16

Exploratory measurements on Apple M3 Pro, 18 GiB memory. Original hero WEBM and timing data remain untouched. Temporary WAVs are deleted after evaluation; derived JSON results and scripts are retained here. No active daemon settings were changed. New models were evaluated outside application dependencies.

## Results we measured

`compare_cached.py` uses five recorded actor turns, then repeats the first 12.636-second clip twenty times per model. CPU defaults are the existing adapter's defaults. Load time is process/model initialization with weights already cached, not a download or a controlled cold filesystem measurement.

| Existing recognizer | Warm median, first clip | Warm p95, first clip | Model load |
| --- | --- | --- | --- |
| Whisper tiny | 351 ms | 609 ms | 3799 ms |
| Whisper base | 721 ms | 904 ms | 535 ms |
| Whisper small | 1693 ms | 2032 ms | 1566 ms |

These are **batch inference times**, excluding recording, turn detection, UI and network. Runs were sequential on a working laptop, not an idle controlled benchmark. Do not compare load values as a robust cold-start ranking.

All three produced understandable results for most of these short English turns. For u3, tiny/base returned “other tests”, while small matched the intended “add a test”. The reference is the script, not a manually certified verbatim transcript: natural delivery differed in places, so these results deliberately do not claim a corpus WER score. Small also revised punctuation in u2. This is evidence for a quality/speed tradeoff, not a general winner.

## Viewer-suggested Nemotron experiment

Issue [#86](https://github.com/noisy/noisy-studio/issues/86) links a community ONNX export; [#84](https://github.com/noisy/noisy-studio/issues/84) requests evaluation. Verified the export card against its linked [NVIDIA source model](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b). The upstream model is streaming and exposes different chunk sizes; Polish is listed separately from its highest-accuracy language tier. The export's 560ms chunk is not a promise of 560ms user-perceived latency.

Tested export revision `3f1f6020667b151d0b6820cc4b8ae4f42b6d35fc`, INT8 encoder/decoder/joiner, sherpa-onnx 1.13.8, four CPU threads, 128-bin features. Loaded in 2433ms. We fed the same five clips in 100ms pieces **without realtime pacing**, followed by one second of silence and input-finished.

| Clip | Recorded duration | Processing time | Audio supplied before first partial |
| --- | --- | --- | --- |
| u1 | 12.64s | 1669ms | 3.5s |
| u2 | 14.28s | 3747ms | 4.1s |
| u3 | 9.62s | 1164ms | 1.8s |
| u4 | 9.27s | 1266ms | 4.1s |
| u5 | 4.74s | 540ms | 2.4s |

The last column is an audio-timeline position, including initial pauses. It is neither wall-clock first-token latency nor delay from speech onset. Nemotron also returned “other tests” in u3. Verdict: **retain as a streaming candidate; do not replace the default based on this evidence.** A paced multilingual/noisy corpus and endpointing comparison is needed before adoption. The application does not yet include a Nemotron adapter.

## Other ticket candidates

- **Canary 180M Flash:** verified the [suggested ONNX repository](https://huggingface.co/csukuangfj/sherpa-onnx-nemo-canary-180m-flash-en-es-de-fr-int8) exists, but it has no model card. Consult the [NVIDIA source](https://huggingface.co/nvidia/canary-180m-flash) for capabilities and terms. Not benchmarked here; language scope matters for Polish use.
- **Parakeet TDT v3:** legitimate [NVIDIA model](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), separate from Nemotron streaming. Not benchmarked here.
- **Qwen3 ASR:** the [suggested export](https://huggingface.co/csukuangfj2/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25) documents another conversion repository; [upstream source](https://github.com/QwenLM/Qwen3-ASR) is available. Validate conversion and runtime separately before shipping; not benchmarked here.
- **GigaAM Russian models / Moonshine uk:** not substitutes for the English/Polish scenario as listed. No blanket license claim from an issue comment is treated as verified.
- **Piper / CoreML Kokoro:** [#48](https://github.com/noisy/noisy-studio/issues/48) remains relevant for output latency. The [current Piper repository](https://github.com/OHF-Voice/piper1-gpl) is GPL; do not assume old project licensing or conflate engine and voice-model terms. Neither was benchmarked in this pass.
- **OpenAI, Fish Audio, ElevenLabs:** reviewed the concerns in [#36](https://github.com/noisy/noisy-studio/issues/36) and [#46](https://github.com/noisy/noisy-studio/issues/46). Do not preserve their historical disqualifications as current facts. OpenAI integration remains a follow-up; voice catalog and streaming semantics are explicitly modeled by the redesign. No new cloud benchmark or billing reconciliation was run.

## Reproduce

Existing cached models (does not download absent ones):

```sh
PYTHONPATH=src python tools/voice-evaluation/compare_cached.py
```

Requires project local dependencies and ffmpeg. Run from the repository root in an isolated process.

Nemotron: use a separate Python environment with `sherpa-onnx==1.13.8`, NumPy and soundfile. Obtain `encoder.int8.onnx`, `decoder.int8.onnx`, `joiner.int8.onnx` and `tokens.txt` from the pinned revision of [the export](https://huggingface.co/Masterx/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-2026-06-11/tree/3f1f6020667b151d0b6820cc4b8ae4f42b6d35fc). Pass their directory explicitly:

```sh
python tools/voice-evaluation/compare_nemotron.py --models /path/to/pinned-model-files
```

The model files and temporary virtual environment are not application assets and are not committed. Re-run results are allowed to differ; retain runtime/hardware details when comparing.

## Cached local synthesis and settings API verification

`verify_local_synthesis.py` exercises the actual Kokoro adapter with three identity-to-voice mappings and validates the generated WAV headers. The recorded run produced mono 24 kHz, 16-bit WAVs for Sarah, Adam and Emma. Its first request includes initialization; subsequent requests are warm. These three samples are a runtime smoke check, not a listening study or latency distribution.

`verify_settings_api.py` starts an isolated loopback server with a temporary provider configuration. It verifies that preparing cached weights leaves the active selection unchanged, applying Kokoro changes only synthesis, and the preview endpoint returns real WAV audio without queueing a conversation message. Neither script changes the running daemon, downloads models, or sends audio to a cloud provider. The updated HTTP test also selects cached Whisper base and verifies complete local readiness with the API-key reader explicitly disabled in that isolated process.

Run either script with `PYTHONPATH=src` in the project's Python environment. Results are retained beside the scripts for reproducibility.

`verify_offline_recognition.py` additionally transcribes the first preserved hero utterance with Whisper base while `HF_HUB_OFFLINE=1`. It refuses incomplete caches, preserves the original recording, and stores the resulting transcript in `offline-recognition-results.json`. This verifies offline loading and recognition on the tested cached model, not accuracy across other languages or models.

## Isolated process memory and warm inference (2026-09-18)

`measure_local_resources.py` uses the first preserved hero utterance (12.64 seconds, English with a Polish accent). Each cached Whisper model runs in a fresh offline process, with one first inference and 20 warm repetitions. Originals and live configuration remain untouched. Runtime versions and raw results are in `local-resource-results.json`.

| Model | Cached snapshot | Peak process RSS | Warm median / p95 |
| --- | ---: | ---: | ---: |
| tiny | 78.2 MB | 373.1 MB | 238 / 265 ms |
| base | 147.9 MB | 549.9 MB | 414 / 481 ms |
| small | 486.2 MB | 961.0 MB | 1244 / 1345 ms |

These are decimal MB and batch inference times after recording, not the full conversational delay. Peak RSS includes Python and runtime overhead. A fresh process does not imply cold disk caches: model load times were 3107 / 368 / 759 ms respectively, so do not rank cold startup from this single sequential run. Machine load also explains variation from the earlier timing pass. No default changes are justified by these results alone.

Reproduce with `PYTHONPATH=src python tools/voice-evaluation/measure_local_resources.py`. Missing models are skipped; `HF_HUB_OFFLINE=1` is set before provider imports. Polish-language recognition, code identifiers, background noise, endpointing, cloud comparison and listening quality remain unmeasured.

## Deterministic noise probe (2026-09-18)

`compare_noise.py` ran all five preserved hero utterances through cached Whisper tiny, base and small: clean audio, plus Gaussian white noise at whole-clip 20 dB and 10 dB SNR. All 45 transcriptions are retained in `noise-results.json`. The seed and noise definition are recorded; generated clips are temporary, and original recordings remain untouched. Run with `PYTHONPATH=src python tools/voice-evaluation/compare_noise.py`.

The most consequential observed change was tiny turning “capital letters” into “couple of letters” at 10 dB in u2. Base retained “capital letters” at both levels, with an extra article. Small kept the same u2 wording across all three conditions. Tiny/base rendered u3 as “other tests” even without added noise; small rendered “add a test.” These examples favor testing base/small over tiny for this particular speaker and wording, not a general quality ranking.

The script references are intended prompts, not independently verified verbatim transcripts, so no word-error-rate score is claimed. Noise is synthetic white noise rather than a real café, keyboard or competing speaker, and RMS includes pauses. Single inference timings are diagnostic only. This closes a reproducible synthetic-noise experiment, not the broader multilingual or real-world noise evaluation. No application default was changed.

The isolated settings API check now also posts the preserved first hero utterance to `/speech-settings/transcribe` using real cached Whisper base. It returned the expected search-related sentence, preserved the selected engines, and queued no agent messages. Its measured 1143 ms includes that request's model/runtime work; it is not a warm distribution or microphone end-to-end latency. The live hardware checks are listed in [MANUAL-CHECKS.md](MANUAL-CHECKS.md); the user elected to perform microphone testing personally.
