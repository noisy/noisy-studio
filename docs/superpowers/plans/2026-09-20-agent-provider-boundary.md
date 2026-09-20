# Agent provider boundary implementation plan (#119)

Goal: keep speech routing, receipts and normalized conversation state independent
of the host's hook protocol. Preserve existing delivery throughout this refactor.

The user approved #119 first, then #120 on 2026-09-20. Evolve the existing harness;
do not introduce a parallel framework or change microphone/provider settings.

- [x] Define transport-independent submission, receipt, readiness and provider
  interfaces alongside normalized lifecycle interpretation. Move hook reply
  fields/types behind the hook compatibility boundary.
- [x] Construct one Claude and one Codex provider. Map legacy registry names to
  their canonical provider without changing conversation keys or speech identity.
- [x] Move hook response rendering and lease decisions out of shared HTTP routing;
  preserve existing HTTP/script protocol and focused compatibility tests.
- [x] Route core utterance submissions through the provider interface, record
  observed delivery outcomes, and exercise a fake push provider through the same
  contract. Keep connection information opaque and queues owned by one consumer.
- [x] Cover identity, participants, routing, availability, expired listeners,
  hidden/closed conversations and persisted state. Keep hook-specific exit-code
  and identity-rewrite assertions at the hook boundary.
- [x] Run Python unit/harness checks and relevant UI/packaging checks; commit
  functional increments and integrate before selecting sockets in #120.

## Independent admission checkpoint for the following ticket

On 2026-09-20, Claude Code 2.1.278 on macOS accepted a synthetic marker from a
separate Python controller process. A temporary SessionStart hook handed its
inherited endpoint and full payload session ID to a private loopback endpoint.
The controller launched the receiving Claude session (stream-json print mode),
waited for its first result, then wrote the user frame while it was idle. An
assistant response contained the exact randomized marker. The sender was not
a child of the receiving Claude process. No messaging token or inbound-policy
setting was supplied or changed. No real conversation speech was used.

This proves admission and idle wake in that tested mode only. Interactive draft
preservation, busy tool behavior, restart handling and rollback still need their
own checks. A production socket write still has no application acknowledgement.

Validation: 423 full-suite checks passed (1 skipped), followed by 54 focused
provider/hook checks after adding the exclusive-consumer guard. Existing
hook-script integration scenarios use the canonical session IDs from #107.
