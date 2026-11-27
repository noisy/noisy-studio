# Org tree · conversation list, project first

Storybook: `Lab/OrgTree` (`OrgTree.stories.ts`). Lab only; production
`AgentTabs` is untouched. This is the second iteration of direction C, which
the product owner picked over A (calm rows) and B (manager desk); the A/B/C
option boards are deleted.

## The model it is designed for

A CEO talks by voice to a few long-lived **manager** conversations. Each
manager delegates to agents (subagents, child threads, Codex tasks). The
primary axis is the **project**: what it is achieving right now. Under a
project sit its managers; under each manager, its delegated agents.

In the agent world the scarce resources are not headcount but:

1. **the CEO's attention** - things that wait for you,
2. **the plan** - money/tokens and the 5-hour and weekly windows,
3. **the machine** - agents running, worktrees.

So every project header shows all three in three lines:

```
[n] noisy-studio                      (2)   <- amber count: what waits for you
    Ship 3.1 with the project list          <- the goal
    1 running   [====|----] 24% of 5h       <- machine | share of the plan window, cap tick
  |  mic Studio manager              2m
  |      Claude Code · main
  |    |  o Org tree lab             3/5
  |    |  ! TestFlight upload    blocked
  |    |  * Settle button spec    review
  |    |  +1 done
```

## Components

| file | job |
|---|---|
| `OrgTree.vue` | the list: projects, "No project", Settled; owns the snooze menu and details card; re-emits row actions as its own events |
| `ProjectBlock.vue` | header (tile, name, focus mark, demand count, goal, resources) + its managers and agents |
| `ResourceStrip.vue` | the header's third line: running count, plan-window meter with cap tick |
| `ManagerRow.vue` | a manager conversation: mic slot, title, wait/wake time, the one status signal, Snooze/Settle on hover |
| `AgentRow.vue` | a delegated agent: state glyph, task, status slot, Pause/Resume/Stop/Review on hover |
| `SettledRow.vue` | one settled or ended conversation, Restore on hover |
| `SnoozeMenu.vue` | presets with wake times, custom field with preview |
| `ProjectCard.vue` | hover card: demands, resources, biggest consumers, Focus / Pause agents / Set cap |
| `orgModel.ts` | the data model and pure rules (demands, running, order, labels) |
| `snooze.ts` | presets and the custom-field grammar |
| `fixtures.ts`, `mockDesk.ts` | story data, and the Playground's make-believe daemon |

## Design decisions

- **Project first, never re-sorted on state.** Projects keep the daemon's
  order so the eye finds them where it left them; only Focus moves one to the
  top. The old your-turn / Working sections are gone: a project's state is
  in its header, not in where it sits.
- **Demands, not waiting.** The amber count is the number of things that
  need an action from you: unheard messages, blocked agents (a decision or an
  approval), finished work to review, and a broken cap. A manager that is
  idle after you heard it is not a demand - it waits for your next order -
  so it shows its wait time in the corner but adds nothing to the count.
- **One meaning per colour, unchanged.** Green: speaking and the mic. Amber:
  needs you (count, blocked, review, over cap). Violet: working. Red: mute
  and errors only (the custom snooze field's "not a time I understand").
  Cyan: the focus mark. Over budget is amber because it is a decision that
  waits for you, not a new colour.
- **The mic is unmistakable and does not move anything.** The mic recipient
  gets a green glyph in its own fixed slot and an inset green edge (a
  shadow, no size change). The status signal keeps the production ladder:
  mute > speaking > queued > working > nothing.
- **Fixed slots everywhere.** Mic slot, time slot, signal slot, agent status
  slot, demand-count slot, focus slot and the running-count slot all have a
  fixed width; long names clip with an ellipsis. Hover actions and both
  overlays sit on the z-axis over what is below.
- **Snoozed stays in its project.** A snoozed manager dims in place with its
  wake time, because its agents may still be running and spending; its own
  messages stop counting until it wakes. Settled holds only settled and
  ended conversations, with their project, folded by default.
- **Done work folds.** Finished agents collapse into "+N done" under their
  manager; click to show them.
- **Conversations without project data** (older harness or daemon) gather
  under one "No project" group below the real projects, with no goal and no
  resource line.
- **Details on hover.** After 500 ms on a project header the card opens to
  the right of the list: the demands spelled out, machine (running, paused,
  worktrees), the plan window (this project's share against everything, the
  reset time), weekly share, tokens and the API-equivalent cost, the cap,
  the five biggest consumers, and the levers.

## Actions (mocked: emitted, no daemon change)

| event | where | args |
|---|---|---|
| `select` | click a manager or settled row | conversation |
| `settle` / `restore` | manager hover / settled hover | conversation |
| `snooze` | manager hover → menu | conversation, wake time (epoch s) |
| `pause` / `resume` / `stop` | agent hover | agent (task id) |
| `review` | agent hover, finished work | agent |
| `focus` | project hover, details card | project, focused |
| `pauseProject` | project hover, details card | project |
| `cap` | details card | project |

## Data the daemon must add to `/status`

What exists today:

- `agents_meta[id]`: `label`, `online`, `status`, `activated_at`,
  `offline_since`, `manual_pos`, `shortcut`, `project` (repository folder
  NAME, from the session's `cwd`), `branch`, `waiting_since`.
- `speaking_agents`, `queued_by_agent`, `muted_agents`, `active_agent` (the
  mic), `activity` - the manager row's states.
- `provider_usage`: per provider and account, the Session (5 h) and Weekly
  windows' `used_percent` and `resets_at`. Account-wide only; no conversation
  or project ids cross that boundary by design.
- `GET /tasks` (not `/status`): task reports per **thread** (the reporting
  conversation, i.e. the manager): `title`, `state`
  (pending/working/blocked/done), `completed`/`total`, `participant` (the
  delegated reporter), `role`, `model`, `review` link and `review_state`,
  `started_at`, `updated_at`.

What the org tree needs added:

1. **Project identity**: `agents_meta[id].project_path` - the repository
   ROOT (worktrees resolved to their main repository), so two worktrees of
   one repo land in one project and two repos with the same folder name do
   not merge. The name alone is not a key. `cwd` is known server-side.
2. **Project goal**: a short "what it is achieving now" line per project.
   Nothing produces it today; candidates are a manager reporting it (a
   `report_goal` MCP tool or a field on `report_task`) or the CEO setting it.
3. **Snooze**: `agents_meta[id].snoozed_until` (epoch s), set by a new
   `POST /snooze {agent, until}`; the daemon wakes it early when it speaks.
   **Settle** needs `settled_at` and `POST /settle` / `/restore`, distinct
   from the session ending.
4. **Per-conversation usage**: `agents_meta[id].usage` = tokens today and
   the share of each plan window this conversation consumed. Hooks already
   see per-turn usage (Claude statusline / transcript, Codex token counts);
   the daemon would sum it per conversation and per delegated participant.
   The project's share is the sum of its conversations'. Must stay free of
   account identifiers, like `provider_usage`.
5. **Task → conversation link**: tasks in `/status` (or a slim
   `tasks_by_agent` summary: counts per state plus the open ones) so the list
   does not poll `/tasks`, and, for a delegated agent that is itself a
   conversation (a child thread, a Codex task), its `conversation` id, so
   the tree can show its live state and its usage instead of only its last
   report.
6. **Concurrency**: worktrees per project (from the conversations' `cwd`s)
   and a per-agent `worktree`.
7. **Controls** (later, not mocked in the daemon): pause / resume / stop of
   a delegated agent, focus (priority) and a per-project cap. All need a
   harness capability; today only the host can stop its own subagents.

## Open questions

- **Which window does the strip show** when a project uses two providers
  (Claude manager, Codex agent)? Now: one window per project in the
  fixtures; proposal: the provider whose window the project uses most, the
  card lists all.
- **Is cost worth showing at all** on a subscription? The card shows tokens
  and an API-equivalent price; the strip shows only the window share.
- **What does Focus do** beyond moving the project to the top: raise its
  agents' priority on the machine, give it more of the window, route
  notifications first? The design only reserves the mark and the lever.
- **Who writes the goal line**, and how does it stay current?
- **Cap semantics**: a soft cap (warn, as drawn) or a hard one (pause the
  project's agents when crossed)?
- **Is a manager idle for a day a demand?** Drawn: no. If it should nudge,
  a stale wait time could turn amber after a threshold.
