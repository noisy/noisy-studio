# Task reporting and human review implementation plan

Goal: show trusted conversation-scoped task progress and explicit review artifacts in the approved compact dashboard workflow.

Architecture: the daemon owns an instance-local persisted task store. Hooks inject thread identity into a minimal MCP reporting interface. Task status and human review are separate; opening a result is never approval. Production UI reuses existing recipient and voice controls.

- [ ] Persisted store: validate bounded reports, revision/idempotency, metadata, URL schemes, independent human review lifecycle, atomic persistence and restart recovery; focused unit tests.
- [ ] API/MCP: report_task and list_tasks; hook-owned conversation identity; HTTP task reads/report and human review; contract and spoofed-identity regression tests.
- [ ] UI: ready-review section, work grouped by real thread, short titles/model metadata, bounded compact review header, explicit recipient and existing PTT/Auto mechanisms; no new audio transport.
- [ ] Companion skill: milestone reporting, truthful role/model/status, stable IDs/revisions, blockers, review artifacts, no self-approval; opt-in documented installation.
- [ ] Final checks and parent review; parent alone merges/pushes/restarts.

Periodic progress pings are deferred. A future design must choose cadence, opt-in, silence rules and cancellation semantics before activating any reminders or agent wakeups. Nothing in this implementation schedules pings.

Identity boundary: existing local daemon/hook architecture trusts local host processes. New MCP operations must be bound to hook-injected identity and reject missing/unknown identity. This does not introduce remote authentication; never represent the localhost API as secure against a hostile local process.
