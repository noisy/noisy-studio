# #138: heard replies incorrectly marked unheard — measurements

Research date: 2026-09-22. No production behavior changed, no daemon restart, no speaker playback. Synthetic English sentences only. Existing dev credentials were used by the normal TTS client without printing credentials or changing configuration.

## Findings

The strongest measured cause is Grok streaming connection cleanup. In two real API runs with the actual mpv streaming player using clocked null output (`--no-config --ao=null`), the player exited successfully but `speak_streaming` returned approximately 2.19 seconds later. The client awaits the player inside the WebSocket context, so context exit/connection close occurs afterward. `_play_prepared` retains the playing claim during that cleanup and then during the 250 ms echo guard. A PTT press in this interval incorrectly records an interruption.

| Probe | Player exit | Streaming call returns | Delay after player exit |
| --- | ---: | ---: | ---: |
| 1 | 2.785 s | 4.971 s | 2.185 s |
| 2 | 9.868 s | 12.056 s | 2.188 s |

An isolated reproduction using the real speech worker and ListenerState, with playback replaced by an immediately completed coroutine and PTT invoked during the echo guard, produced `unheard — interrupted by push-to-talk`. Thus the echo-guard race exists independently of audio content or provider.

## Generated audio

Four texts were synthesized through each of the Grok batch and streaming APIs: Orion, English, speed 1.0, MP3. Streaming capture drained chunks without playing them. FFmpeg decoded mono float PCM at 24 kHz; each final 10 ms RMS frame above a threshold defines an approximate last nonquiet frame. These are amplitude measurements, not a speech detector or a claim about human audibility.

| Sample | Decoded duration | Tail below −35 dBFS | Tail below −45 dBFS | Tail below −55 dBFS |
| --- | ---: | ---: | ---: | ---: |
| batch-1 | 1.800 s | 0.410 s | 0.320 s | 0.200 s |
| batch-2 | 2.760 s | 0.320 s | 0.210 s | 0.150 s |
| batch-3 | 3.816 s | 0.336 s | 0.216 s | 0.216 s |
| batch-4 | 8.616 s | 0.326 s | 0.236 s | 0.206 s |
| stream-1 | 2.064 s | 0.264 s | 0.144 s | 0.134 s |
| stream-2 | 2.856 s | 0.326 s | 0.226 s | 0.196 s |
| stream-3 | 3.576 s | 0.396 s | 0.206 s | 0.186 s |
| stream-4 | 8.136 s | 0.596 s | 0.226 s | 0.206 s |

Synthetic texts:

1. Yes, it is working.
2. The microphone is ready. You can speak now.
3. I saved the changes locally, but I have not pushed them.
4. First, open the application. Then choose your microphone. Finally, send a short voice message to confirm that everything works.

## Interpretation and recommended next step

The measured Grok files have 144–320 ms of trailing quiet audio at −45 dBFS. This can create an additional interval after the last perceived word, but the larger confirmed issue needs no silence heuristic: a successfully completed player is still treated as interruptible for about 2.44 seconds (connection cleanup plus echo guard).

Separate playback completion from provider/network cleanup and microphone echo muting. Report successful player completion at the playback boundary and settle/release the matching card there, without allowing an earlier genuine interruption or explicit skip to be overwritten. Keep the echo guard independently. Last network chunk received or written is not playback completion: in the long probe, the last chunk arrived at 2.535 s but the player exited at 9.868 s.

Do not introduce the suggested 90–95% or under-one-second completion shortcut. It can discard meaningful final words, and a percentage scales poorly with message length. First fix and test the proven post-player window; measure any remaining hardware/player or encoded-silence window independently before deciding on trimming or silence-aware completion.

Regression coverage should exercise PTT after successful playback while provider cleanup is blocked, PTT during the echo guard, true mid-playback interruptions, explicit skip, replay/other-agent requeue behavior, and player failure.

## Limits and reproducibility

This is a small exploratory sample from one provider, voice, speed, and language. Do not generalize its silence thresholds or WebSocket latency to other providers. Clocked null output does not measure physical device buffering, acoustic output, or real-device teardown. The isolated echo reproduction establishes control-flow behavior rather than measuring a physical press. No end-to-end human test is required to demonstrate these two post-playback defects.

Local scripts, MP3 samples, and raw JSON are retained in `/tmp/noisy-studio-138-research/`: `probe.py`, `results.json`, `player_probe.py`, `player-results.json`, and `reproduce.py`. The tests used the unchanged repository TTS clients; streaming capture replaced only `_play_from_stream`, and the player timing probe replaced only its command with clocked null output and recorded `unregister_player`. No API payloads or private configuration were saved in this report.
