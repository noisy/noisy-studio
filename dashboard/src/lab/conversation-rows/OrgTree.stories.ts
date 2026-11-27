import type { Meta, StoryObj } from "@storybook/vue3";
import OrgTree from "./OrgTree.vue";
import { useMockDesk } from "./mockDesk";
import { AGENT_STATES, BENCH, BUCKY, DESK, LEGACY, LONG, MANAGER_STATES, NOW, STUDIO, WEBSITE } from "./fixtures";

const EVENTS = ["select", "settle", "restore", "snooze", "pause", "resume", "stop", "review", "focus", "pauseProject", "cap"] as const;
const handlerName = (event: string) => `on${event[0].toUpperCase()}${event.slice(1)}`;
const CONVERSATIONS = [...new Set([...DESK, MANAGER_STATES].flatMap((project) => project.managers.map((manager) => manager.id)))];

/** The conversation list as an org tree, project first (direction C, second
 *  iteration). Each project shows its goal, what runs, its share of the plan
 *  window and what waits for you; managers and their delegated agents hang
 *  underneath. Hover a row for its actions, hover a project header for its
 *  details card. Every action is emitted (see the Actions panel); the
 *  Playground story also applies them. See README.md in this folder. */
const meta = {
  title: "Lab/OrgTree",
  component: OrgTree,
  args: { projects: DESK, now: NOW, micId: "studio", viewedId: "studio", settledOpen: false, openMenu: null, openCard: null, pinnedHover: [] },
  argTypes: {
    micId: { control: "select", options: [null, ...CONVERSATIONS] },
    viewedId: { control: "select", options: [null, ...CONVERSATIONS] },
    openMenu: { control: "select", options: [null, ...CONVERSATIONS] },
    ...Object.fromEntries(EVENTS.map((event) => [handlerName(event), { action: event }])),
  },
  decorators: [() => ({ template: '<div style="width:268px"><story /></div>' })],
} satisfies Meta<typeof OrgTree>;
export default meta;
type Story = StoryObj<typeof meta>;

/** The realistic desk: five projects in the daemon's order, the legacy
 *  conversation under "No project", and Settled folded at the bottom. The
 *  mic is on the Studio manager (green edge + mic glyph). */
export const Desk: Story = {};

/** Settled unfolded: one ended conversation and one you settled, each with
 *  its project, Restore on hover. */
export const SettledOpen: Story = { args: { settledOpen: true } };

/** One manager with three delegated agents: one running with progress,
 *  one blocked on your Apple login, one waiting for your review. The two
 *  that need you make the project's amber count 2; the finished agent
 *  folds into "+1 done" (click to show it). */
export const OneManagerThreeAgents: Story = { args: { projects: [STUDIO] } };

/** Two managers on one project: the app manager is speaking to you (green
 *  equalizer outranks its queued message), the backend manager is working
 *  with one Codex agent under it. The mic is on the speaking one. */
export const TwoManagers: Story = { args: { projects: [BUCKY], micId: "bucky-app", viewedId: "bucky-api" } };

/** Nothing runs, nothing waits, 0 % of the window: the quiet case. A
 *  manager waiting a day for your next order is not a demand, so there is
 *  no amber count; the wait time stays in its corner. */
export const IdleProject: Story = { args: { projects: [WEBSITE], micId: "web", viewedId: "web" } };

/** Over its cap: four benchmark agents used 46 % of the 5 h window against
 *  a 30 % cap. The meter and its label turn amber and the broken cap joins
 *  the things waiting for you. The details card is open on it: biggest
 *  consumers, and the Pause agents / Change cap levers. */
export const OverBudget: Story = { args: { projects: [BENCH], micId: "bench", viewedId: "bench", openCard: BENCH.id } };

/** Long project, conversation, branch and task names clip with an ellipsis
 *  and never push the time, signal or status slots. Also: a paused agent
 *  (resume on hover) and a snoozed second manager showing its wake time. */
export const LongNames: Story = { args: { projects: [LONG], micId: "assets", viewedId: "assets" } };

/** A conversation from an older harness or daemon: no folder, so no
 *  project, goal or usage. It gathers under "No project" below the real
 *  projects. This one is muted (red) with two messages held back. */
export const LegacyWithoutProject: Story = { args: { projects: [STUDIO, LEGACY], micId: "fitatu", viewedId: "fitatu" } };

/** Every manager row state in one project, in fixed slots: mic + your turn,
 *  speaking, messages to hear, working (activity replaces line 2), muted,
 *  snoozed (dimmed, wake time in the corner). */
export const ManagerStates: Story = { args: { projects: [MANAGER_STATES], micId: "m-mic", viewedId: "m-mic" } };

/** Every delegated agent state: running with and without progress, queued,
 *  blocked, to review, paused, and finished (folded; click "+1 done"). */
export const AgentStates: Story = { args: { projects: [AGENT_STATES] } };

/** Hover affordances drawn as if hovered: Snooze/Settle on the manager,
 *  Pause/Stop on running work, Review/Stop on finished work. Real hover
 *  shows the same on any row. */
export const HoverActions: Story = { args: { projects: [STUDIO], pinnedHover: ["studio", "s1", "s3"] } };

/** The snooze menu, open: presets with the wake time they resolve to, and a
 *  custom field ("45m", "2h", "14:30", "fri 9:00", "tomorrow") that previews
 *  its wake time. Type in it; Set emits `snooze`. Opens from any manager's
 *  Snooze button. */
export const SnoozeMenuOpen: Story = { args: { projects: [STUDIO], openMenu: "studio" } };

/** The project details card, open (it also opens after hovering any project
 *  header for half a second): what waits for you, machine, plan window with
 *  the project's share against everything, weekly share, tokens and
 *  API-equivalent cost, cap, biggest consumers, and Focus / Pause agents /
 *  Set cap. */
export const DetailsCard: Story = { args: { projects: [STUDIO], openCard: STUDIO.id, pinnedHover: [STUDIO.id] } };

/** A focused project moves to the top and carries the focus mark; the rest
 *  keep their order. Unfocus from the header's hover actions. */
export const Focused: Story = { args: { projects: DESK.map((project) => (project.id === BUCKY.id ? { ...project, focused: true } : project)) } };

/** No conversations at all. */
export const Empty: Story = { args: { projects: [], micId: null, viewedId: null } };

/** The desk with a make-believe daemon behind it: click a manager to move
 *  the mic, Settle / Restore, Snooze, pause, resume and stop agents, Review,
 *  Focus, Pause a whole project. Events still reach the Actions panel. */
export const Playground: Story = {
  render: (args) => ({
    components: { OrgTree },
    setup() {
      const desk = useMockDesk(args.projects, args.now, args.micId);
      // Keyed by event name: v-on adds the "on" itself.
      const handlers = Object.fromEntries(EVENTS.map((event) => [event, (...values: never[]) => {
        (desk[event as keyof typeof desk] as ((...values: never[]) => void) | undefined)?.(...values);
        (args[handlerName(event) as keyof typeof args] as ((...values: never[]) => void) | undefined)?.(...values);
      }]));
      return { args, desk, handlers };
    },
    template: `<OrgTree :projects="desk.projects.value" :now="args.now" :mic-id="desk.micId.value" :viewed-id="desk.micId.value"
      :settled-open="true" v-on="handlers" />`,
  }),
};
