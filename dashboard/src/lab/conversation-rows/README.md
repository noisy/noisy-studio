# Conversation rows · three options

Storybook: `Lab/ConversationRows` (OptionACalmRows, OptionBManagerDesk,
OptionCOrgTree). Lab only; production `AgentTabs` is untouched.

## The model these are designed for

Not T3's model. T3 shows many short threads per project as equal rows. Our
user keeps one long-lived **manager** conversation per area (about four at
once), talks to each by voice like a CEO to managers, and each manager
delegates to subagents or child threads. So the list must:

1. foreground the few managers,
2. make it obvious which one has the **mic** and which **needs you**,
3. show delegated work as **subordinate** to its manager, never as peers,
4. still offer **Settle** and **Snooze** on hover (no ✕ on rows).

Each board shows the realistic desk (four managers + Settled) and labelled
specimens of the remaining states (hovered with details, muted, legacy
without project, long names, snooze menu open), at the real 268 px column
width, dark and light. The dashboard has no light theme yet: the light
tokens in `ConversationRows.vue` are a proposal.

## Options

The full "always / hover / section / card / dropped from T3" lists live in
`optionNotes.ts` and are printed above each board.

- **A · Calm rows** - today's three lines, line 3 becomes the delegated work
  summary ("2 running · 1 to review"). Keeps the your-turn / Working
  sections. Smallest change; managers still jump between sections.
- **B · Manager desk** - one card per manager in hotkey order, never
  re-sorted. Line 2 says in words what it needs from you; MIC chip + green
  border; a segmented bar of delegated tasks on the card's bottom edge.
  Settled rows collapse to one line.
- **C · Org tree** - manager as tile + two lines, children always visible as
  indented tree lines with progress / review / blocked. Status as ring and
  badges on the tile.

## Shared decisions

- Idle shows no glyph. The signal ladder is unchanged: mute > speaking >
  queued > working.
- Colours keep their single meaning: green speaking and mic, amber waiting
  (queued, blocked, to review), violet working, red mute only.
- Hover actions are opaque overlays; nothing reflows.
- Snooze presets show their wake time; Custom takes "45m", "2h", "fri 9:00"
  or a date. A snoozed manager waits under Settled with its wake time and
  comes back early if it speaks or queues a message.
- Settle moves it to Settled; Restore brings it back. Removing a
  conversation entirely moves to the context menu, not a row ✕.

## Data the daemon does not send yet

- the conversation's working folder (`path`; known server-side as `cwd`),
- snooze state and wake time,
- task-progress reports linked into `/status` per conversation (they exist
  in the task-progress store: title, state, completed/total, participant,
  role, model, review state).
