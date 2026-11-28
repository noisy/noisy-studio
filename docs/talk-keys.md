# Talk keys

Global keys that open the microphone for a conversation from any app.

## What exists today (v3)

- **Push to talk** (`hold`, `toggle`, `scratch`): the mic goes to the
  conversation already selected in the dashboard.
- **A conversation's own key**: right-click a row and pick "Set a key…" to
  set it. The key stays with that conversation and survives restarts. Pressing it hands
  that conversation the mic wherever it sits in the list, and brings it back
  if it was settled. The registry keeps each chord on one conversation at
  most (`ConversationRegistry.set_talk_key`).
- **Tab 1–4** (`tab1`–`tab4`, F16–F19 on the dev machine): positional. Tab N
  is the N-th visible conversation, top to bottom in the dashboard list
  (project order, then order inside the project), skipping conversations
  that have their own key (`ListenerState.tab_shortcuts`, capped by
  `TAB_SHORTCUT_COUNT`).

## Decision: Tab 1–4 stay for v3 and go in v4 (2026-11-28)

Positional keys follow the list, so they break muscle memory. Dragging a
project or a row, settling a conversation, or giving one its own key
renumbers every conversation after it. Keys that belong to a
conversation do not have this problem.

- **v3 keeps Tab 1–4** as a fallback for people who already bound them. They
  cost nothing when unbound, and removing them mid-version would silently
  unbind keys people use.
- **v4 removes them.** Talk keys belong to a conversation, or to a project or
  its manager once v4 has that concept.

Removal checklist for v4:

1. Daemon: drop `tab1`–`tab4` from the hotkey action map,
   `talk_to_tab` and `TAB_SHORTCUT_COUNT`. Migrate a stored `tabN` binding
   onto the conversation that held position N at upgrade time, and say so
   in the release notes.
2. Dashboard: remove the "…to a specific tab" pane from Settings > Hotkeys
   and the positional key cap on rows. Remove `"tab1"`–`"tab4"` from
   `HotkeyAction`.
3. Update the Storybook fixtures (`daemon.fixture.ts`, `HotkeysSettings`
   stories) in the same commit.
