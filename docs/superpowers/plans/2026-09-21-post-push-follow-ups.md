# Follow-ups after the local changes are pushed

Status: published on 2026-09-22 after the implementation reached remote main and Krzysztof authorized the issue updates and contributor reply.

## Ticket checklist

- [x] PR #90 — [superseded implementation update posted](https://github.com/noisy/noisy-studio/pull/90#issuecomment-5770570128), including the upgrade guide. PR remains open pending final disposition.
- [x] #99 — native audio cleanup completed; [resolution posted](https://github.com/noisy/noisy-studio/issues/99#issuecomment-5770568846) and issue closed.
- [x] PR #103 — [contributor reply posted](https://github.com/noisy/noisy-studio/pull/103#issuecomment-5770570003). PR remains open pending final disposition.
- [x] Confirm the X profile for the invitation: https://x.com/realnoisycoder (provided by Krzysztof).
- [x] #134 and #135 — microphone timeline fixes posted and both issues closed.
- [x] #136 — restart recovery resolution posted and issue closed.
- [ ] #80 — broader rebrand issue remains open; signed macOS upgrade/permission validation remains a release check, and the broader media audit needs confirmation before closing it.

Implementation notes: [native audio](2026-09-21-native-audio-only.md), [microphone timeline](2026-09-21-microphone-timeline.md), [restart recovery](2026-09-21-claude-restart-recovery.md).

## Reply posted to PR #103

Target: https://github.com/noisy/noisy-studio/pull/103

Hi Igor! Thank you for contributing to Noisy Studio and for taking the time to investigate and fix this. Seeing our first community contribution was a really special moment, and we appreciate the effort you put into it.

While your PR was open, we made substantial changes on the V3 desktop branch and decided to support native apps only, retiring Docker support and the browser audio mode entirely. That changed the scope of the fix: instead of keeping browser audio available alongside native audio, we removed the old browser capture, playback transport, activation banner, and fallback paths, and migrated existing audio settings to native devices.

We reviewed your PR, but the implementation it targets has now been removed as part of that broader change, so we couldn't merge it as written. We've addressed the underlying issue in the V3 implementation on main, including preventing a native microphone failure from switching the app back to browser capture.

I'd also love to hear more about your experience with Noisy Studio. If you're up for it, would you be open to a quick chat—around 15 minutes, or whatever works for you—to exchange ideas? You can reach me on my new X account: [@realnoisycoder](https://x.com/realnoisycoder). No pressure at all; written feedback here is welcome too.

Feedback from people using the project is crucial to making it better. I'd love to understand what you're trying to accomplish, what you like, what gets in your way, and what's missing. That would really help me decide where to take V3 next.

Thank you again for helping improve Noisy Studio. We'd be very happy to see more contributions from you as V3 takes shape!
