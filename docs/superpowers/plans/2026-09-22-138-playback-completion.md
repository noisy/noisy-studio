# Playback completion implementation plan

Goal: fix #138 by separating successful playback from transport cleanup and echo muting.
Architecture: streaming providers emit an optional playback-completion callback; the shared speech worker atomically settles its card before cleanup, then applies the independent echo guard. Completion must not overwrite an earlier interruption/skip. Provider-specific trimming and word tracking remain separate.
Tech stack: Python asyncio, threaded speech worker, pytest.

- [ ] Add regression coverage for completion before streaming cleanup, echo-tail PTT, earlier interruption/skip, cleanup failure, and streaming player outcome.
- [ ] Implement completion callback through Grok adapter and player paths; normalize player failures and register buffered playback for interruption.
- [ ] Add atomic state completion, release playback claim before echo guard, preserve completed status on later transport cleanup failure.
- [ ] Run focused and full unit/harness checks, commit locally. Validate with isolated silent real streaming playback before scheduling a dev restart if required.

No fixed-duration trimming, percentage rule, UI feature, or word-alignment plumbing. Keep dev data/config unchanged. Do not push this implementation yet.
