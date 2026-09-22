# Playback completion implementation plan

Goal: fix #138 by separating successful playback from transport cleanup and echo muting.
Architecture: streaming providers emit an optional playback-completion callback; the shared speech worker atomically settles its card before cleanup, then applies the independent echo guard. Completion must not overwrite an earlier interruption/skip. Provider-specific trimming and word tracking remain separate.
Tech stack: Python asyncio, threaded speech worker, pytest.

- [x] Add regression coverage for completion before streaming cleanup, echo-tail PTT, earlier interruption/skip, cleanup failure, and streaming player outcome.
- [x] Implement completion callback through Grok adapter and player paths; normalize player failures and register buffered playback for interruption.
- [x] Add atomic state completion, release playback claim before echo guard, preserve completed status on later transport cleanup failure.
- [x] Run focused and full unit/harness checks, commit locally. Validate with isolated silent real streaming playback before scheduling a dev restart if required.

No fixed-duration trimming, percentage rule, UI feature, or word-alignment plumbing. Keep dev data/config unchanged. Do not push this implementation yet.

Word-level progress feature tracked separately in #139: https://github.com/noisy/noisy-studio/issues/139.

Verification: 460 unit/harness tests passed, 1 skipped. A real Grok streaming request with clocked null output settled the card at player completion; PTT at that point returned no interruption and status remained played through the following 2.476 seconds of cleanup. This verifies API/player integration silently; real hardware timing remains a separate observation. Dev restart scheduled with 60-second postponable countdown, retaining the existing dev store.

Dev rollout completed: replacement listener started without a port conflict on 7765 using the preserved dev store. Status reports Jabra Link 380; a real spoken response succeeded and the user’s incoming voice reached this conversation. Immediate-PTT hardware confirmation is now available for the user to test.
