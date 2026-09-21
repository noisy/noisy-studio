# Claude restart recovery implementation plan

Goal: resolve #136 without waking idle conversations unnecessarily or replaying speech.

Approved design: preserve Claude connection registrations privately, validate and restore them after conversation loading, and retain existing durable wake correlation. Use ACTION NEEDED with a bordered explanation above the transcript only when automatic recovery cannot proceed.

## Implementation sequence

- [x] Persist versioned registrations in the existing private Claude delivery journal. Remove invalidated/ended registrations. Restore only matching, visible, active Claude conversations after the registry loads. Reuse socket validation at its boundary; do not infer paths or restore listener leases.
- [x] Exercise a new daemon/provider instance with the same storage: fresh speech, previously queued speech, pending wake, duplicate late wake, missing/stale connection, closed/hidden conversation, and old protocol. Keep pending wake records intact across restart. Commit the backend increment.
- [x] Add actionable provider failure wording and an optional notice in Bubble above its transcript. Use ACTION NEEDED for unavailable delivery; keep normal waiting unchanged. Update Storybook and focused UI coverage. Commit the UI increment.
- [x] Run appropriate Python and dashboard checks, and a real isolated Claude session across a daemon restart. Record evidence and limitations. Roll into dev with the postponable 60-second restart and verify microphone/config isolation.

Connection metadata stays in the provider journal, never the public conversation payload. Socket sends retain target-session and ownership guards. A successful write is not delivery confirmation. Older installations without stored endpoints need one fresh hook event before future restarts recover automatically. Corrupt connection rows must be ignored; a corrupt delivery database must not be silently discarded because it contains deduplication history.

Dev rollout: source daemon restarted gracefully on 7765 using the dev configuration; Jabra Link 380 selected and current dashboard build served. Storybook Action Needed preview is available on local port 6007. Warning label and border are yellow independently of the accent palette; the label has no exclamation mark.
