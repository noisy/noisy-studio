# #138: silence handling and word-level playback progress

Research date: 2026-09-22. Follow-up to the playback-completion report. Investigation only: no daemon changes, speaker output, restart, or push.

## Questions and evidence

Can trailing silence be treated as a fixed duration? No evidence supports that. Thirteen additional streaming generations compare three lengths with identical final words, three repeats each, plus another voice, two speeds, and a whispered ending. Baseline is Orion, English, speed 1.0, MP3, latency optimization 1. The last phrase in all length-controlled samples is “Everything is ready.”

| Length | Repeats | Decoded duration | Trailing audio below −45 dBFS |
| --- | ---: | ---: | ---: |
| short | 3 | 1.416–1.560 s | 226–290 ms |
| medium | 3 | 7.176–7.656 s | 156–316 ms |
| long | 3 | 20.064–20.616 s | 160–376 ms |

The long samples do not have proportionally longer tails. Even identical text/settings vary. These exploratory observations do not establish a distribution or universal bound. RMS thresholds describe signal level, not assured inaudibility. Quiet consonants, breath, expressive sounds and whispers need protection.

## Provider documentation

The [xAI TTS guide](https://docs.x.ai/developers/model-capabilities/audio/text-to-speech) and [API reference](https://docs.x.ai/developers/rest-api-reference/inference/voice) list no trailing-silence guarantee or trimming parameter. They document MP3/WAV/PCM output, character timestamps, and latency optimization focused on initial chunks. Timestamps add alignment work; streaming can return timings alongside audio. `audio.done` confirms generation/transmission, not speaker completion. Connections can serve multiple utterances. These capabilities do not establish a safe amount to cut.

## Trimming cost and safety

Across these 13 files, vectorized 10 ms RMS analysis of decoded audio took 0.032–0.639 ms (per-file median of 100 runs). FFmpeg subprocess startup plus complete MP3 decoding took 37.3–195.5 ms (per-file median of three runs); most were 37–79 ms, with one 195 ms outlier. This is analysis throughput, not a complete production trim/playback benchmark. No re-encoding, hardware output or accuracy validation is included.

A batch prototype can scan backward from EOF, retain a protective margin, and cut only a sufficiently quiet final region. Slicing decoded PCM is cheap and avoids a second lossy encode. It still needs empirical safety checks; a quiet threshold can classify speech as silence. Exact-zero-only trimming is more conservative but cannot remove nonzero quiet tails. Stereo policy should preserve sound on either channel.

For streaming, future speech is unknown until generation ends. Keep a bounded decoded tail buffer and inspect it at EOF; release older samples continuously. This preserves internal pauses but may add buffer latency and only removes the final quiet region still retained. A filter that stops on the first quiet gap is unsafe: it can stop at an ordinary pause. [FFmpeg silenceremove documentation](https://ffmpeg.org/ffmpeg-filters.html#silenceremove) describes threshold, duration and retained-silence controls; its stop-period semantics require care. Switching to PCM could avoid MP3 decoding but changes bandwidth and the playback path; it was not benchmarked here.

## Word progress experiment

Six live streaming requests alternated timestamps off/on (three each), using the same 22-word synthetic text and existing MP3 settings. Audio was captured, never played. Connection setup is excluded from the following first-audio measurements.

| Timestamps | First audio, each run | Median |
| --- | --- | ---: |
| False | 366 ms, 462 ms, 436 ms | 436 ms |
| True | 370 ms, 376 ms, 410 ms | 376 ms |

No startup penalty was visible in this tiny sample; it does not prove zero overhead or that timestamps make synthesis faster. Timing metadata arrived in two events per enabled request, roughly 1.09–1.26 s and 1.88–2.02 s after sending. The last metadata event had zero audio bytes: consumers must process metadata independently of nonempty audio. Timings covered the entire sample and increased across those events; wider chunking, speed, normalization, language and expressive-tag cases still require validation.

Grouping the returned characters into 22 words and looking up the last completed word with binary search averaged 0.168 microseconds over 100,000 local lookups. At a synthetic playback position of 3.0 seconds the mapped completed prefix was: “I checked the microphone and saved your settings.” This benchmarks local lookup only, not alignment accuracy or live UI latency.

The other half is a trustworthy playback clock. [mpv documents audio-pts](https://mpv.io/manual/stable/#properties) as audio playback position accounting for driver delay, plus time-pos and seeking. This is a better basis than bytes downloaded, bytes handed to the player, or wall time since synthesis started. Driver timing remains an estimate; afplay/ffplay fallbacks need their own supported clock or reduced functionality. Live IPC/hardware accuracy has not been measured in this follow-up.

Proposed flow: start audio immediately; accept alignment metadata asynchronously; store it alongside the exact cached rendering (voice, speed, text, provider). On interruption, save playback position and the last confidently completed word. Metadata may arrive late, so enrich the card afterward without holding the microphone or initial playback. Resume from the partially played word or a small preceding context boundary using the SAME cached audio. Do not regenerate the remainder and reuse old offsets. Pauses, seeks and replay must use the player clock, not a stopwatch.

The UI can honestly show “played up to…” / “continue from…” with uncertainty. It cannot know that the user heard or understood each word, or that OS/headphone volume was audible. Timestamp estimates and driver buffering also prevent a literal exact-hearing guarantee. For providers without alignment, use time-based progress initially; optional background forced alignment may enrich it later without blocking playback. Forced alignment/VAD models and other providers were not benchmarked.

## Options and recommendation

| Path | Benefit | Cost / limitation |
| --- | --- | --- |
| Separate player completion from network cleanup and echo guard | Fixes the proven ~2.44 s post-player window without changing audio | First priority; preserve true interruption/skip outcomes |
| Background or overlapping connection closure; persistent sessions | Removes transport teardown from critical path, potentially improves next request | Lifecycle, cancellation and session ownership complexity; still not an audio clock |
| Conservative final-region trimming on decoded samples | Can remove variable tails based on actual content | Threshold safety, codec work; streaming needs bounded buffering |
| Timestamp metadata plus playback position | Word progress and resume; can avoid judging trailing silence by duration alone | Provider support, late/approximate alignment, player-clock integration |
| PCM/WAV instead of MP3 | Simpler sample-level analysis and slicing | Bandwidth/packaging/player changes; no promise the generated tail disappears |
| Background forced alignment / VAD | Potential fallback across providers | Extra compute, accuracy and deployment burden; do not block initial playback |
| Fixed seconds, percentage cutoff, first-quiet-gap stop | Simple | Reject: can discard real words or misclassify internal pauses |

Recommended sequence: fix the proven completion/cleanup bug first; prototype nonblocking timestamp capture and playback-position tracking separately; consider conservative EOF trimming only if the remaining tail is still a problem. Do not bundle a speculative audio-trimming policy into the basic status fix. No implementation choice has been finalized by this research.

## Local artifacts

Scripts and raw results remain in `/tmp/noisy-studio-138-research/`: `expanded.py`, `expanded-results.json`, thirteen generated MP3s, `timestamps.py`, `timestamp-results.json`, six timestamp MP3s, `map_benchmark.py`, and `word-mapping.json`. All texts are synthetic. Future validation should include more repetitions, voices, languages, punctuation, quiet endings, disconnects, and actual hardware playback before claiming provider-independent safety.
