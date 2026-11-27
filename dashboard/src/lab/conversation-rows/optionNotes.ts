/** What each option shows where - rendered above its board and mirrored in README.md. */
export type OptionKey = "a" | "b" | "c";

export interface OptionNotes {
  name: string;
  pitch: string;
  /** true: managers move between "your turn" and "Working" like today. */
  sectioned: boolean;
  always: string[];
  hover: string[];
  section: string[];
  card: string[];
  droppedFromT3: string[];
}

export const OPTION_NOTES: Record<OptionKey, OptionNotes> = {
  a: {
    name: "A · Calm rows",
    pitch: "The smallest step from today: T3's three calm lines, but line 3 is the manager's delegated work instead of a branch. Managers still move between your turn and Working.",
    sectioned: true,
    always: [
      "Line 1: project logo + name, wait time top-right (\"4m\")",
      "Line 2: title + one signal slot (amber count, green equalizer, violet dots, red mute); idle draws nothing",
      "Line 3: delegated work summary \"2 running · 1 to review\" (amber when it needs you); branch only when nothing is delegated",
      "Mic: green bar on the left edge (overlay)",
    ],
    hover: [
      "Snooze + Settle icons over the wait time, opaque plate, no reflow",
      "Details card after 500 ms to the right, over the frame, listing each delegated task",
    ],
    section: [
      "Your turn: wait time",
      "Working: title dims, no wait time, violet dots in the signal slot",
      "Settled: dimmed, \"2h\" or wake time, hover offers Restore",
    ],
    card: [
      "Project + path", "Full title", "What it needs from you", "Delegated tasks: state, progress, who (subagent, model)",
      "Branch", "Harness", "Started · last activity", "Tab hotkey", "Mic", "Short id",
    ],
    droppedFromT3: [
      "Branch on every row: a manager outlives branches; its children carry them, so branch moved to the card",
    ],
  },
  b: {
    name: "B · Manager desk",
    pitch: "Four cards in hotkey order that never re-sort: the place of a manager is muscle memory, like a desk. Each card says in words what it needs from you; its bottom edge is a segmented bar of delegated work.",
    sectioned: false,
    always: [
      "Line 1: Tab hotkey key, title (bold), MIC chip slot, wait time",
      "Line 2: one sentence of what it needs, in its colour: \"Your turn · 2m\", \"3 messages to hear\", \"Speaking now\", \"Working · reading CI logs\", \"Muted\"",
      "Line 3: project · delegated summary (or branch)",
      "Bottom edge: one 2 px segment per delegated task (violet running, amber blocked/to review, grey done)",
      "Mic: green border + inset bar + MIC chip",
    ],
    hover: [
      "Snooze + Settle icons over the MIC/time corner",
      "Compact tooltip after 500 ms: full title, path · branch, harness · started, delegated summary, hotkey",
    ],
    section: [
      "No Working section: a busy manager keeps its place; its line 2 turns violet instead",
      "Settled: the card collapses to a one-line row under a Settled fold; Restore puts it back on the desk",
    ],
    card: ["Full title", "Path · branch", "Harness · started", "Delegated summary", "Tab hotkey"],
    droppedFromT3: [
      "Re-sorting rows by state: with ~4 managers, position + hotkey is how you find them by voice and by eye",
      "The Working section: busy is shown in place, not by moving the row away",
      "Project as the row's headline: the manager's name is the headline, project is an attribute",
    ],
  },
  c: {
    name: "C · Org tree",
    pitch: "The manager is the parent and its delegated work hangs underneath, always visible, like an org chart. Status sits on the project tile as a ring and badges, like presence on a chat avatar.",
    sectioned: false,
    always: [
      "Manager: 28 px project tile + title / project and branch (or live activity while working)",
      "Tile ring: violet working (pulses), green speaking; badges: amber count, red mute, green mic",
      "Children: indented one-line rows on a tree line: state glyph, title, progress \"3/5\" or \"review\"/\"blocked\" in amber",
      "Open work first; done work folds; more than 3 children fold into \"+N more\"",
    ],
    hover: [
      "Labelled \"Snooze\" and \"Settle\" buttons float over the manager's right side",
      "Child hover: tooltip with who did it (subagent, model) and the blocked reason",
      "Details card after 500 ms with the full task list and metadata",
    ],
    section: [
      "No Working section: managers keep their place",
      "Settled: grey tile, children hidden, \"2h\" or wake time; hover offers Restore",
    ],
    card: [
      "Project + path", "Full title", "What it needs from you", "All delegated tasks with who/progress",
      "Branch", "Harness", "Started · last activity", "Tab hotkey", "Mic", "Short id",
    ],
    droppedFromT3: [
      "Flat list of equal threads: child threads are drawn as subordinate lines, never as peer rows",
      "Re-sorting by state and the Working section",
      "Three-line rows: the tree already spends height on children, so the manager is two lines",
    ],
  },
};
