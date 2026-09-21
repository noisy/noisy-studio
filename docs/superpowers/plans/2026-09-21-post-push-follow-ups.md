# Follow-ups after the local changes are pushed

Status: local preparation only. Do not post comments or close tickets yet.
Publish the contributor reply only after the relevant implementation is on remote main and Krzysztof authorizes posting it. Recheck issue status before taking any action.

## Ticket checklist

- [ ] PR #90 — after pushing the independently implemented V3 rename, explain that it supersedes the conflicted PR and link the manual upgrade guide. Do not merge or close the old PR yet.

- [ ] #99 — native audio cleanup: after pushing, link the implementation and update the issue.
- [ ] PR #103 — post the thank-you draft below after pushing; agree its final disposition with Krzysztof.
- [x] Confirm the X profile for the invitation: https://x.com/realnoisycoder (provided by Krzysztof).
- [ ] #134 and #135 — microphone timeline fixes: after pushing, review and update the issues.
- [ ] #136 — Claude connection recovery after daemon restart: after pushing, review and update the issue.

Implementation notes: [native audio](2026-09-21-native-audio-only.md), [microphone timeline](2026-09-21-microphone-timeline.md), [restart recovery](2026-09-21-claude-restart-recovery.md).

## Draft reply to PR #103 — not posted

Target: https://github.com/noisy/noisy-studio/pull/103

Hi Igor! Thank you for contributing to Noisy Studio and for taking the time to investigate and fix this. Seeing our first community contribution was a really special moment, and we appreciate the effort you put into it.

While your PR was open, we made substantial changes on the V3 desktop branch and decided to support native apps only, retiring Docker support and the browser audio mode entirely. That changed the scope of the fix: instead of keeping browser audio available alongside native audio, we removed the old browser capture, playback transport, activation banner, and fallback paths, and migrated existing audio settings to native devices.

We reviewed your PR, but the implementation it targets has now been removed as part of that broader change, so we couldn't merge it as written. We've addressed the underlying issue in the V3 implementation on main, including preventing a native microphone failure from switching the app back to browser capture.

I'd also love to hear more about your experience with Noisy Studio. If you're up for it, would you be open to a quick chat—around 15 minutes, or whatever works for you—to exchange ideas? You can reach me on my new X account: [@realnoisycoder](https://x.com/realnoisycoder). No pressure at all; written feedback here is welcome too.

Feedback from people using the project is crucial to making it better. I'd love to understand what you're trying to accomplish, what you like, what gets in your way, and what's missing. That would really help me decide where to take V3 next.

Thank you again for helping improve Noisy Studio. We'd be very happy to see more contributions from you as V3 takes shape!
