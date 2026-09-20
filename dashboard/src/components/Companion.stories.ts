import type { Meta, StoryObj } from "@storybook/vue3";
import { defineComponent, ref } from "vue";
import Companion, { type CompanionAgent, type CompanionMessage } from "./Companion.vue";

/* Compact conversation, status, and session controls across window sizes. */
const meta: Meta<typeof Companion> = {
  title: "Widget/Companion",
  component: Companion,
  // The widget is small; Storybook's padded canvas made it float in a sea
  // of empty space. Centered crops the frame to the content.
  parameters: { layout: "centered" },
};
export default meta;
type Story = StoryObj<typeof Companion>;

/** Legacy names stay private in the header and avatar tooltips (#107). */
export const UnsafeSavedNames: Story = {
  args: {
    agents: [
      { name: "session-1", label: "/private/example/session-1", voice: "lux", active: true },
      { name: "C:\\projects\\session-2", voice: "eve" },
    ],
  },
};

const SHORT = "On it.";
const MEDIUM = "The retry logic is ready. I’m checking that queued events survive a redeploy.";
const LONG = "The event stays in the queue until the consumer confirms delivery. The regression test now covers a redeploy during processing, including recovery of pending messages. I’m checking the final dashboard state before wrapping up.";

const FEED: CompanionMessage[] = [
  { id: 1, role: "claude", text: "I'm ready." },
  { id: 2, role: "user", text: "let's wire up the companion" },
  { id: 3, role: "claude", text: MEDIUM },
];

const AGENTS: CompanionAgent[] = [
  { name: "stream-day-2", voice: "lux", active: true },
  { name: "chat", voice: "eve" },
  { name: "talk-me-through", voice: "atlas", unread: true },
];

const base = { voice: "lux", maxHeight: 200, agents: AGENTS };

/* ---- states ------------------------------------------------------- */

/** Cold start: the daemon seeds one line so the widget is never empty. */
export const ColdStart: Story = {
  args: { ...base, mode: "idle", feed: [{ id: 1, role: "claude", text: "I'm ready." }] },
};

/** A conversation with nothing in it yet - switching to a fresh agent. */
export const EmptyConversation: Story = { args: { ...base, mode: "idle", feed: [] } };

/** Claude holding the floor: its portrait lit, the spectrum at rest. */
export const ClaudeSpeaking: Story = { args: { ...base, mode: "claude", feed: FEED } };

/** The user mid-sentence, transcript growing as they speak. */
export const UserTalking: Story = {
  args: { ...base, mode: "user", feed: FEED, liveText: "okay so the next thing", level: 0.6 },
};

/** Holding push-to-talk before a word is said: lit, but nothing to show. */
export const ListeningSilent: Story = {
  args: { ...base, mode: "user", feed: FEED, liveText: "", level: 0.02 },
};

/* ---- type sizing --------------------------------------------------- */

/** Short and long messages share a stable, readable type scale. */
export const MessageSizes: Story = {
  args: {
    ...base,
    mode: "claude",
    maxHeight: 260,
    feed: [
      { id: 1, role: "user", text: LONG },
      { id: 2, role: "claude", text: MEDIUM },
      { id: 3, role: "user", text: SHORT },
    ],
  },
};

/** A short reply remains legible after a long history. */
export const ShortAfterLong: Story = {
  args: {
    ...base,
    mode: "claude",
    feed: [
      { id: 1, role: "user", text: LONG },
      { id: 2, role: "claude", text: LONG },
      { id: 3, role: "user", text: SHORT },
    ],
  },
};

/** More than fits: the thread scrolls, pinned to the newest. */
export const Overflowing: Story = {
  args: {
    ...base,
    mode: "claude",
    feed: Array.from({ length: 12 }, (_, i) => ({
      id: i,
      role: i % 2 ? "claude" : ("user" as const),
      text: i % 3 ? MEDIUM : SHORT,
    })) as CompanionMessage[],
  },
};

/* ---- the agent rail ------------------------------------------------ */

/** Two conversations - the common case. */
export const RailTwo: Story = {
  args: {
    ...base,
    mode: "claude",
    feed: FEED,
    agents: [
      { name: "stream-day-2", voice: "lux", active: true },
      { name: "chat", voice: "eve", unread: true },
    ],
  },
};

/** Five - where a vertical rail stops being readable, if it does. */
export const RailCrowded: Story = {
  args: {
    ...base,
    mode: "claude",
    feed: FEED,
    agents: [
      { name: "stream-day-2", voice: "lux" },
      { name: "chat", voice: "eve" },
      { name: "talk-me-through", voice: "atlas", active: true },
      { name: "word-up", voice: "iris", unread: true },
      { name: "test16", voice: "kepler" },
    ],
  },
};

/** No rail at all: one conversation, portrait only. */
export const RailNone: Story = {
  args: { ...base, mode: "claude", feed: FEED, agents: [] },
};

/* ---- interactive ---------------------------------------------------- */

/** Drive the whole flow by hand: idle -> user talks -> commits -> reply. */
const Playground = defineComponent({
  components: { Companion },
  setup() {
    const mode = ref<"idle" | "user" | "claude">("idle");
    const feed = ref<CompanionMessage[]>([{ id: 0, role: "claude", text: "I'm ready." }]);
    const liveText = ref("");
    const level = ref(0);
    let nextId = 1;

    const talk = () => {
      mode.value = "user";
      liveText.value = "";
      level.value = 0.5;
      const words = "okay so the next thing I want is the agent rail".split(" ");
      words.forEach((w, i) =>
        setTimeout(() => {
          liveText.value = liveText.value ? `${liveText.value} ${w}` : w;
          level.value = 0.3 + Math.random() * 0.5;
        }, i * 180),
      );
      setTimeout(() => {
        feed.value = [...feed.value, { id: nextId++, role: "user", text: liveText.value }];
        liveText.value = "";
        level.value = 0;
        mode.value = "idle";
      }, words.length * 180 + 300);
    };

    const reply = (text: string) => {
      mode.value = "claude";
      feed.value = [...feed.value, { id: nextId++, role: "claude", text }];
      setTimeout(() => (mode.value = "idle"), 1500);
    };

    return { mode, feed, liveText, level, talk, reply, SHORT, LONG };
  },
  template: `
    <div style="display:flex;flex-direction:column;gap:12px;align-items:flex-start">
      <div style="display:flex;gap:8px">
        <button @click="talk()">user talks</button>
        <button @click="reply(SHORT)">short reply</button>
        <button @click="reply(LONG)">long reply</button>
      </div>
      <Companion
        :mode="mode" voice="lux" :feed="feed" :live-text="liveText"
        :level="level" :max-height="200"
        :agents="[
          { name: 'stream-day-2', voice: 'lux', active: true },
          { name: 'chat', voice: 'eve' },
        ]"
      />
    </div>
  `,
});

export const Playground_Flow: StoryObj = { render: () => Playground };

/** Queued-to-speak badges: the active head and a rail head both carrying
 *  counts, plus the 9+ cap. */
/** The live (composing) bubble must FLOAT over a scrolled-up feed - same
 *  contract as the dashboard composer. Scroll the thread up: the amber
 *  bubble stays pinned to the bottom edge. */
export const LiveOverScroll: StoryObj = {
  render: () => ({
    components: { Companion },
    setup: () => ({
      feed: Array.from({ length: 14 }, (_, i) => ({
        id: i + 1,
        role: i % 2 ? "claude" : "user",
        text: `message number ${i + 1} to make the thread scroll`,
      })),
    }),
    template: `
      <div style="width: 460px">
        <Companion mode="user" voice="lux" :feed="feed" :max-height="180"
          live-text="I am still talking and this must stay visible" />
      </div>
    `,
  }),
};

/** Compact window: conversation and session controls must remain reachable. */
export const NarrowStrip: StoryObj = {
  render: () => ({
    components: { Companion },
    setup: () => ({ SHORT }),
    template: `
      <div style="width: 300px">
        <Companion
          mode="idle" voice="lux" :max-height="220"
          :feed="[
            { id: 1, role: 'user', text: 'does it still fit?' },
            { id: 2, role: 'claude', text: SHORT },
          ]"
          :agents="[
            { name: 'stream-day-4', voice: 'lux', active: true, waiting: 2 },
            { name: 'chat', voice: 'eve' },
          ]"
        />
      </div>
    `,
  }),
};

export const WaitingBadges: StoryObj = {
  render: () => ({
    components: { Companion },
    setup: () => ({ SHORT }),
    template: `
      <div style="width: 520px">
        <Companion
          mode="idle" voice="lux" :max-height="200"
          :feed="[{ id: 1, role: 'claude', text: SHORT }]"
          :agents="[
            { name: 'stream-day-4', voice: 'lux', active: true, waiting: 3 },
            { name: 'chat', voice: 'eve', unread: true, waiting: 12 },
            { name: 'website', voice: 'atlas' },
          ]"
        />
      </div>
    `,
  }),
};

export const Muted: Story = { args: { ...base, muted:true, voiceMuted:true, feed:FEED } };
export const Offline: Story = { args: { ...base, offline:true, feed:FEED } };
export const Working: Story = { args: { ...base, activity:'Running the dashboard tests', feed:FEED } };
export const PendingReplies: Story = {
  args:{...base, feed:[...FEED, {id:4,role:'claude',text:'The checks passed. Ready when you are.',zone:'pending',statusKind:'off',statusLabel:'Unheard'}]},
};
export const LongSessionName: Story = {
  args:{...base,feed:FEED,agents:[{name:'codex / investigate-checkout-performance-and-retry-handling',voice:'lux',active:true}]},
};
