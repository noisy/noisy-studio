# Claude socket delivery implementation plan (#120)

Goal: wake the same Claude conversation with completed user speech using its
registered inbox, while preserving identity, ordering, and truthful delivery state.
The issue's approved design is the implementation specification. #119 must land
first; the core must use its transport-independent provider contract.

## Constraints

One Claude provider. Socket delivery is its default private implementation;
retain hooks for deliberate rollback through one internal construction choice.
Never race consumers, automatically fall back, or retry an uncertain send.
Socket write completion is unconfirmed, not an application receipt. Keep inbound
host controls unchanged. Never print live endpoints, session IDs or private state.
Do not change Codex delivery, microphone settings or release versions.

## Checkpoints

- [x] Establish independent-process admission before enabling the default path.
  Use the existing probe protocol with a private loopback handoff from a receiving
  Claude SessionStart hook; the sender must not be the receiving session's child.
  Record Claude version, OS, mode and observed reply/hold/refusal separately from
  unit tests. Test with synthetic speech only, without manipulating host policy.
- [x] Complete/integrate #119 first, preserving current hook delivery. Define
  registration, utterance submission, receipts, normalized activity and readiness.
  Verify a fake push implementation through the same core-facing contract.
- [x] Implement a bounded Unix-socket sender inside the Claude provider. Validate
  endpoint ownership/type and full target identity. Register from the inherited
  endpoint at SessionStart without allowing participants to replace the parent.
- [x] Preserve the 2-second continuation window and 20-second cap, original IDs,
  recipient and ordering. Track queued, unavailable, written-unconfirmed and
  uncertain states without dropping or automatically replaying ambiguous sends.
- [x] Make hook delivery inactive in socket mode, including stale drain requests.
  Keep identity injection, activity and lifecycle observations. Centralize rollback
  and document session restart/re-registration requirements.
- [x] Test socket I/O once at its boundary; mock it in provider/core tests. Cover
  absent/stale endpoints, partial writes, restart, participant isolation, closed
  tabs, grouped speech, and no duplicate delivery. Update relevant UI scenarios.
- [x] Verify independent live wake, busy tools, keyboard draft preservation and
  deliberate rollback. Use the postponed 60-second shutdown for dev changes;
  verify Jabra microphone and preserve pending speech before handing over.

A missing endpoint after daemon restart requires registration from the target
session; do not infer it from a UUID or silently reuse a different conversation.
No claims of exactly-once execution or confirmation without measured evidence.

Implementation notes: #119 is committed separately as c95e026 and integrated
into local main before socket activation. Source behavior, recovery, cancellation,
rollback and the packaged entry points were checked. Live evidence is recorded in
../specs/2026-09-20-claude-inbox-evidence.md. Operational recovery and deliberate
rollback are documented in ../../claude-inbox-delivery.md.

The dev reload uses the postponable countdown. No new signed release is published
by this task; existing packaged installations need the matching app/plugin update.
