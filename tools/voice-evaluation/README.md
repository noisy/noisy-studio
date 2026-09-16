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

`verify_settings_api.py` starts an isolated loopback server with a temporary provider configuration. It verifies that preparing cached weights leaves the active selection unchanged, applying Kokoro changes only synthesis, and the preview endpoint returns real WAV audio without queueing a conversation message. Neither script changes the running daemon, downloads models, or sends audio to a cloud provider.

Run either script with `PYTHONPATH=src` in the project's Python environment. Results are retained beside the scripts for reproducibility.

`verify_offline_recognition.py` additionally transcribes the first preserved hero utterance with Whisper base while `HF_HUB_OFFLINE=1`. It refuses incomplete caches, preserves the original recording, and stores the resulting transcript in `offline-recognition-results.json`. This verifies offline loading and recognition on the tested cached model, not accuracy across other languages or models.
