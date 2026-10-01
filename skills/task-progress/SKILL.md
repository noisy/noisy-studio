---
name: task-progress
description: Report Noisy Studio task progress, delegated work, blockers and explicit review artifacts through its MCP tools. Use while doing multi-step work when report_task and list_tasks are available, or when the user requests dashboard progress reporting.
---

# Task progress and review

Use `report_task` to keep the dashboard informative at meaningful milestones: starting a concrete task, completing a step, discovering a blocker, or producing something ready for the user. Do not report every tool call or narrate an invented percentage.

- Choose a stable short `task_id` for each independently reviewable work item. Start `revision` at 1; increment it when the report changes. Each report replaces the previous report for that ID, so include the metadata and review target you want retained.
- Retry an uncertain submission with exactly the same ID, revision and fields. On a revision conflict, read `list_tasks` and reconcile; do not blindly overwrite newer work.
- Set `state` to `pending`, `working`, `blocked`, or `done`. Report actual completed/total steps together only when a meaningful count exists; otherwise omit both. Counts do not predict elapsed or remaining time.
- Use concise, specific noun phrases for task titles: name the result or problem, not the action you are taking. Prefer “New onboarding flow” over “Preview the new onboarding flow”, and “Next TestFlight build” or “TestFlight build 430” over “Prepare the next TestFlight build”. Omit filler such as “Prepare”, “Preview”, and “Work on”; retain distinguishing details such as a build number. Put explanations in the spoken update or review artifact, not the title.
- Keep the title stable as progress changes; review availability is already shown separately. Use a blocked title that identifies the missing prerequisite. Never mark incomplete work done to clear a panel.
- Report `role` and `model` only when known; omit unknown values. Never guess a teammate's model from its name.
- Leave `agent_id` and `reporter_id` unset. The host hook supplies the real conversation and reporter identities. Never copy an identity from another thread or try to attach work to it.

## Delegation

The main conversation can report several delegated work items, each with a stable participant identifier and clear role. Subagents reporting directly are restricted to their hook-supplied participant identity; they cannot update the manager's or another participant's work. Agree on stable task IDs before reporting the same item from multiple agents. Parent review and integration remain the parent's responsibility.

## Ready for review

When a task is done and there is an artifact the user should inspect, include `review: {label, url, direct?}` with a descriptive action label and the exact absolute HTTP(S) URL. Local preview URLs are fine; filesystem paths and guessed links are not supported. If there is no artifact, omit review rather than inventing one.

Example: `report_task(task_id="audio-settings", revision=3, title="Compact audio settings", state="done", completed=3, total=3, role="Dashboard agent", review={"label":"Review settings preview","url":"http://localhost:6038/?path=/story/lab-audio--compact"})`.

Set `review.direct: true` for destinations that refuse iframe embedding, such as GitLab. The dashboard currently opens all reviews directly. The wrapper is retained behind `REVIEW_IFRAMES_ENABLED` in `dashboard/src/components/task-progress/reviewPage.ts`; when enabled, omitted/false uses the wrapper and true still opens directly. The whole review item opens the link; only after opening does it reveal Approve and Reject. Human rejection is stored as `review_state: "rejected"`; read it with `list_tasks`, address the feedback, and report a new revision for fresh review. Never approve or reject on the user’s behalf.

Task completion, opening a review, and human approval are separate. No MCP tool approves work on the user's behalf. A changed report revision requires fresh review even if the URL is unchanged. Read approval state through `list_tasks`; do not infer it from silence or a visited link.

## Availability and installation

This skill ships inside the Noisy Studio plugin's `skills/` directory. Existing installations need the updated plugin/MCP server and hooks before the tools appear. For another harness, explicitly install this skill using its documented skill mechanism; do not silently edit global agent configuration. If tools or identity hooks are unavailable, provide a concise written status and explain that dashboard reporting is unavailable.

Periodic pings are a future feature, not part of this skill. Do not schedule timers, automation, reminders or agent wakeups merely to keep progress fresh.
