# Task reporting and human review implementation plan

Goal: show trusted conversation-scoped task progress and explicit review artifacts in the approved compact dashboard workflow.

Architecture: the daemon owns an instance-local persisted task store. Hooks inject thread identity into a minimal MCP reporting interface. Task status and human review are separate; opening a result is never approval. Production UI reuses existing recipient and voice controls.

- [x] Persisted store: validate bounded reports, revision/idempotency, metadata, URL schemes, independent human review lifecycle, atomic persistence and restart recovery; focused unit tests.
- [x] API/MCP: report_task and list_tasks; hook-owned conversation identity; HTTP task reads/report and human review; contract and spoofed-identity regression tests.
- [x] UI: ready-review section, work grouped by real thread, short titles/model metadata, bounded compact review header, explicit recipient and existing PTT/Auto mechanisms; no new audio transport.
- [x] Companion skill: milestone reporting, truthful role/model/status, stable IDs/revisions, blockers, review artifacts, no self-approval; opt-in documented installation.
- [ ] Final checks and parent review; parent alone merges/pushes/restarts.

Periodic progress pings are deferred. A future design must choose cadence, opt-in, silence rules and cancellation semantics before activating any reminders or agent wakeups. Nothing in this implementation schedules pings.

Identity boundary: existing local daemon/hook architecture trusts local host processes. New MCP operations must be bound to hook-injected identity and reject missing/unknown identity. This does not introduce remote authentication; never represent the localhost API as secure against a hostile local process.

Review notes: the embedded artifact has an opaque sandbox origin (scripts/forms only), with an always-available separate-tab fallback. Browser policy can prevent rendering a page and cannot be bypassed. The UI does not mark iframe load as approval. The main agent remains the feedback recipient for delegated artifacts, and feedback controls stay disabled until the daemon confirms that recipient.

Validation: backend unit/harness suite passed with an isolated empty configuration (558 passed, one skipped), plus an HTTP round-trip persistence test. Eight new UI tests cover review lifecycle, recipient refusal/recording safety, PTT release, URL gating and stale polling. TypeScript/Vite and Storybook builds pass. Existing Provider Limits and Stage Crew filename/title mismatches remain for their owners to resolve during integration.
