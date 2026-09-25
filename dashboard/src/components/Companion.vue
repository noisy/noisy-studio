<script setup lang="ts">
/** Compact conversation surface shared by the desktop window and browser companion. */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Bubble from "./Bubble.vue";
import VoiceAvatar from "./VoiceAvatar.vue";
import type { AvatarSetId } from "../avatars/catalog";
import { conversationLabel } from "../conversationLabel";

export interface CompanionMessage {
  role: "user" | "claude";
  text: string;
  /** Timeline zone from machines/chat.ts. "pending" is still waiting its
   *  turn - a transcript not picked up yet, or a reply queued behind the
   *  speaker - and renders dimmed below the line, as in the dashboard. */
  zone?: "done" | "active" | "pending";
  /** The utterance's own id. Keying by position makes Vue reuse a bubble
   *  for a different message - switch conversation and the second bubble
   *  morphs into the other agent's second bubble instead of being replaced. */
  id?: string | number;
  /** Status chip, SAME semantics as the dashboard (bubbleStatus.statusChip):
   *  the widget must represent transcribing/queued/unheard identically. */
  statusKind?: import("./bubbleStatus").StatusKind;
  statusLabel?: string;
  /** User recording/transcription stays visible even when the mic is idle. */
  inFlight?: boolean;
}

/** One conversation in the rail, in the dashboard's own tab order. */
export interface CompanionAgent {
  /** The agent's ID - a session hash. Identity, never shown to a human. */
  name: string;
  /** The human title; legacy names are used only when safe to display. */
  label?: string;
  voice: string;
  /** The conversation currently on screen: bigger, lit, never dimmed. */
  active?: boolean;
  /** Something happened here while you were looking elsewhere. */
  unread?: boolean;
  /** Messages queued to be SPOKEN in this conversation - shown as a small
   *  numeric badge on the head (0/undefined = no badge). */
  waiting?: number;
}

const props = withDefaults(
  defineProps<{
    mode?: "claude" | "user" | "idle";
    muted?: boolean;
    voiceMuted?: boolean;
    offline?: boolean;
    /** Use the session header as the frameless desktop window's drag region. */
    draggable?: boolean;
    voice?: string;
    /** Marketing scenes can pin a portrait style without changing preferences. */
    avatarSet?: AvatarSetId;
    /** Mixed feed, oldest first; freshest renders at the bottom. */
    feed?: CompanionMessage[];
    /** Live transcript while the user talks (grows as they speak). */
    liveText?: string;
    /** Pixel height of the visible thread; older messages scroll away. */
    maxHeight?: number;
    /** Scripted previews always follow the current line, including after seeking. */
    followLatest?: boolean;
    /** Live mic level, 0..1. Drives the spectrum. */
    level?: number;
    /** What the agent is doing between messages ("running Bash", …), from
     *  the daemon's activity line. Null when it is not working. */
    activity?: string | null;
    /** Other conversations, oldest at the top. The ACTIVE one is `voice`. */
    agents?: CompanionAgent[];
    /** Queued-to-speak count for the single-conversation portrait. */
    waiting?: number;
  }>(),
  {
    mode: "idle",
    muted: false,
    voiceMuted: false,
    offline: false,
    draggable: false,
    voice: "rex",
    feed: () => [],
    liveText: "",
    maxHeight: 200,
    level: 0,
    agents: () => [],
    waiting: 0,
    activity: null,
  },
);

/* The spectrum is never dead.
 *
 * A row of flat bars reads as "broken", not "quiet", so silence gets a slow
 * breathing motion and the mic level rides on top of it. Each bar has its
 * own phase and its own weight, so the shape stays uneven the way a real
 * spectrum does - a symmetrical wave looks like a screensaver.
 *
 * Driven by rAF rather than CSS: the bars have to follow a value that
 * changes, and a keyframe animation cannot.
 */
const BAR_COUNT = 7;
const BAR_PHASE = [0, 1.9, 3.4, 0.7, 2.6, 4.3, 1.2];
const BAR_WEIGHT = [0.55, 0.95, 0.7, 1, 0.78, 0.9, 0.6];
const IDLE_FLOOR = 7;   // bar height at rest, in viewBox units
const IDLE_SWING = 3.5; // how far the breathing moves it
const PEAK = 46;        // height at full level

/* Each message carries its own size, decided by its own length and never
 * revisited. A short line gets big type, a long one gets small type, and
 * neither changes afterwards - no measuring, no re-fitting, no flicker.
 *
 * Thresholds are in characters, which is a coarse proxy for how much room
 * the text needs. It does not have to be exact: being one size out on a
 * borderline message is invisible, while a message that resizes after you
 * have started reading it is not.
 */
function sizeOf(text: string): string {
  const n = text.trim().length;
  if (n <= 90) return "size-l";
  if (n <= 260) return "size-m";
  return "size-s";
}

const grownHeight = ref(0);

/* How much room the thread is allowed: never more than the window can show.
 * The floating window is resized by hand and remembers its last size, so the
 * requested height is a wish, not a fact - a widget that insists on 220px
 * inside a 160px window puts its newest line out of reach. */
const ceiling = ref(Number.POSITIVE_INFINITY);
const threadHeight = computed(() =>
  Math.min(Math.max(props.maxHeight, grownHeight.value), ceiling.value),
);


/** Keep the thread inside the window it is in. Type size is not its job. */
async function refit() {
  const el = scroller.value;
  const box = root.value;
  if (!el || !box) return;

  // Measure the window the widget is ACTUALLY IN - once it floats, that is
  // the picture-in-picture window, not the page that owns this code.
  const view = box.ownerDocument.defaultView ?? window;
  const chrome = box.offsetHeight - el.offsetHeight;
  // The drag handle is part of the card header; reserve only outer padding.
  const container = box.closest<HTMLElement>('.companion-window');
  const windowGutter = container ? 16 : 32;
  ceiling.value = Math.max(32, (container?.clientHeight || view.innerHeight) - chrome - windowGutter);

  const room = Math.min(props.maxHeight, ceiling.value);
  const content = el.scrollHeight;
  // A tall conversation may earn more room, but never more than the window
  // can show: a thread taller than its window cannot be scrolled to, and the
  // newest line would be stranded below the edge.
  grownHeight.value =
    content > room ? Math.min(content, props.maxHeight * 2.5, ceiling.value) : 0;
  await nextTick();
  // The thread just changed size, so whether it scrolls at all may have
  // flipped - scroll events alone never fire on a thread that never scrolls.
  updateClipped();
}

/* Never show the raw session id. The dashboard titles its tabs from
 * agent_labels; the widget used the agents map's KEYS, which are the ids -
 * so the same conversation read "stream-day-7" in one place and a hash in
 * the other, in the title bar and on every bubble. */
const activeAgent = computed(() => props.agents.find(a => a.active));
const sessionName = computed(
  () => activeAgent.value
    ? conversationLabel(activeAgent.value.label, activeAgent.value.name)
    : 'Companion',
);

/* Where the pointer is, in the widget's own coordinates, so the tooltip can
 * be drawn OUTSIDE the avatar rail. The rail scrolls horizontally, and
 * anything painted inside it is clipped - which is why the leftmost
 * avatar's tooltip vanished when it lived there. */
const tip = ref<{ text: string; x: number; y: number } | null>(null);
function showTip(event: Event, text: string) {
  const btn = event.currentTarget as HTMLElement;
  const box = root.value;
  if (!box) return;
  const b = btn.getBoundingClientRect();
  const r = box.getBoundingClientRect();
  tip.value = { text, x: b.left - r.left + b.width / 2, y: b.top - r.top };
}
const waitingCount = computed(() => activeAgent.value?.waiting || props.waiting || props.feed.filter(m => m.zone === 'pending').length);
const stateLabel = computed(() => {
  if (props.offline) return 'Offline';
  if (props.muted) return 'Microphone muted';
  if (props.mode === 'user') return 'Recording';
  if (props.mode === 'claude') return 'Speaking';
  if (props.voiceMuted) return 'Playback muted';
  if (props.activity) return 'Working';
  return waitingCount.value ? `${waitingCount.value} waiting` : 'Ready';
});

const emit = defineEmits<{ (e: "select", name: string): void }>();
void emit;


const bars = ref<number[]>(new Array(BAR_COUNT).fill(IDLE_FLOOR));
// Smoothed level: the raw feed is jumpy at 20fps, and bars that snap look
// like noise. Attack fast so speech feels immediate, release slow so the
// spectrum falls away instead of collapsing.
const smoothed = ref(0);
let frame = 0;

function animate(now: number) {
  const target = Math.max(0, Math.min(1, props.level));
  const k = target > smoothed.value ? 0.35 : 0.08;
  smoothed.value += (target - smoothed.value) * k;

  const t = now / 1000;
  bars.value = BAR_PHASE.map((phase, i) => {
    const breath = props.mode === "user" ? Math.sin(t * 1.6 + phase) * IDLE_SWING : 0;
    const voice = smoothed.value * PEAK * BAR_WEIGHT[i];
    // Flicker keeps the peaks from moving as one block while speaking.
    const flicker = smoothed.value * Math.sin(t * 11 + phase * 2.3) * 6;
    return Math.max(2, IDLE_FLOOR + breath + voice + flicker);
  });
  frame = requestAnimationFrame(animate);
}

let sizeWatch: ResizeObserver | undefined;

/* NARROW MODE is a class flipped straight from the resize observer.
 * (It briefly rode a View Transition; verdict after trying it live: not
 * worth it - the morph fought window dragging and cost reactivity.) */
const NARROW_BELOW_PX = 420;
const narrow = ref(false);

onMounted(() => {
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) frame = requestAnimationFrame(animate);
  // A ResizeObserver rather than a window listener: it fires when the widget
  // is dragged into the floating window and when that window is resized,
  // both of which change the space available - and neither of which raises a
  // resize event on the page that owns this code.
  if (root.value) {
    narrow.value = root.value.offsetWidth < NARROW_BELOW_PX; // first paint: no animation
    /* DEBOUNCED on purpose: Chrome skips a view transition whose viewport
     * is being resized mid-flight, and the threshold is always crossed
     * mid-drag - so an immediate flip technically ran and visually never
     * showed. Waiting for the resize to settle lets the morph play. */
    let settle: ReturnType<typeof setTimeout> | undefined;
    sizeWatch = new ResizeObserver(() => {
      // Cheap per tick: a class flip and the type refit. The bottom re-pin
      // (scroll work) waits for the resize to settle.
      if (root.value) narrow.value = root.value.offsetWidth < NARROW_BELOW_PX;
      void refit().then(updateClipped);
      clearTimeout(settle);
      settle = setTimeout(() => stickToBottom(false).then(updateClipped), 160);
    });
    sizeWatch.observe(root.value);
    const container = root.value.closest('.companion-window');
    if (container) sizeWatch.observe(container);
  }
});
onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  sizeWatch?.disconnect();
});

/* A wide invisible "grab zone" along the right edge: the hairline thumb
 * grows to full size when the pointer is within GRAB_ZONE_PX of the edge,
 * not just on the 6px bar itself (too thin to target). */
const GRAB_ZONE_PX = 44;
const nearScroll = ref(false);
function trackPointer(e: MouseEvent): void {
  const box = (e.currentTarget as HTMLElement).getBoundingClientRect();
  nearScroll.value = box.right - e.clientX <= GRAB_ZONE_PX;
}

/* The arrival animation is for ONE new message sliding in. Switching
 * conversation replaces every bubble at once, and animating all of them
 * together reads as the whole panel shaking before it settles. So: animate
 * an arrival, never a replacement. */
const animateArrival = ref(true);
let lastIds: string[] = [];
let primed = false;

watch(
  () => props.feed.map((m) => String(m.id ?? "")).join("|"),
  (joined) => {
    const ids = joined ? joined.split("|") : [];
    const shared = ids.some((id) => id && lastIds.includes(id));
    // Nothing in common with what was on screen = a different conversation.
    /* "Replaced" cannot be judged by what we came FROM.
     *
     * The previous version required the old feed to be non-empty, so
     * leaving an empty conversation looked like a first render and skipped
     * the hide - which is why switching back from a thread with no messages
     * showed the type resizing, while every other switch did not. What
     * matters is that the arriving messages share nothing with the ones on
     * screen, however few of those there were. */
    const replaced = primed && !shared && ids.length > 0;
    animateArrival.value = !replaced;
    lastIds = ids;
    primed = true;
  },
  { immediate: true },
);

/* Same split as the dashboard's conversation log: what already happened,
 * then the busy line, then what is still waiting its turn. The zones come
 * from machines/chat.ts - the widget must not invent its own rules about
 * what "delivered" means, which is exactly what it did before. */
const history = computed(() => props.feed.filter((m) => m.zone !== "pending" && !m.inFlight));
const composingMessages = computed(() => props.feed.filter((m) => m.inFlight));
const pendingMessages = computed(() => props.feed.filter((m) => m.zone === "pending"));
/** Room for two; the rest become a count, so a queue cannot fill a widget. */
const WAITING_SHOWN = 2;
const waitingShown = computed(() => pendingMessages.value.slice(0, WAITING_SHOWN));
const waitingExtra = computed(() => Math.max(0, pendingMessages.value.length - WAITING_SHOWN));

const scroller = ref<HTMLElement | null>(null);
const root = ref<HTMLElement | null>(null);
/* Follow the newest message, unless the reader has scrolled away.
 *
 * The live transcript updates several times a second while the user talks,
 * and every update used to yank the thread back down - so reading anything
 * older was impossible. Standard chat behaviour: stay pinned while you are
 * at the bottom, stop following the moment you scroll up, resume when you
 * come back down.
 */
const BOTTOM_SLACK_PX = 48;
const following = ref(true);

/* True when content is CLIPPED below the viewport - the bottom fade shows
 * only then: fully scrolled down, the newest message must end SHARP. */
const clippedBelow = ref(false);

/* True only when the thread actually scrolls. Both fades mean "there is
 * more conversation past this edge", so on a thread that fits entirely
 * they are a lie: the top fade eats the first bubble and the widget reads
 * as cropped and half-empty. Reported from the marketing hero, where a
 * lone "I'm ready." bubble looked broken. */
const overflowing = ref(false);

function updateClipped() {
  const el = scroller.value;
  if (!el) return;
  overflowing.value = el.scrollHeight - el.clientHeight > 2;
  clippedBelow.value = el.scrollHeight - el.scrollTop - el.clientHeight > 2;
}

function onScroll() {
  const el = scroller.value;
  if (!el) return;
  following.value = el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_SLACK_PX;
  updateClipped();
}

async function stickToBottom(smooth = true): Promise<void> {
  await nextTick();
  const el = scroller.value;
  if (!el || (!following.value && !props.followLatest)) return;
  // Two frames: the first lands after Vue patches the DOM, the second after
  // the browser has laid it out. Scrolling in between aims at a height that
  // is about to change, which is how the newest message kept ending up just
  // below the edge.
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
}

/* ONE watcher, in order: fit first, then scroll.
 *
 * There used to be two on the same signals - one scrolling, one re-fitting.
 * The scroll started against the old layout, then the re-fit changed the
 * type size and the height underneath it, and a smooth scroll aimed at a
 * scrollHeight that no longer existed stopped short of the newest message.
 * Fitting has to finish before anything decides where the bottom is.
 */
watch(
  () => [props.feed.map(m => `${m.id}:${m.text}:${m.statusLabel}`).join("|"), props.liveText, props.maxHeight, props.activity],
  async () => {
    await refit();
    // Jump, do not glide: after a re-fit the layout has already moved, and a
    // smooth scroll would animate from a position that is no longer real.
    await stickToBottom(false);
  },
  { immediate: true },
);
</script>

<template>
  <div ref="root" class="companion" :class="{ narrow }"  @mousemove="trackPointer" @mouseleave="nearScroll = false">
    <header class="companion-header" :class="{ 'drag-strip': draggable }" :title="draggable ? 'Drag this bar to move the desktop window. Resize at the edges.' : undefined">
      <span v-if="draggable" class="drag-hint">
        <svg aria-hidden="true" width="10" height="14" viewBox="0 0 10 14" fill="currentColor">
          <circle cx="2" cy="3" r="1" /><circle cx="8" cy="3" r="1" />
          <circle cx="2" cy="7" r="1" /><circle cx="8" cy="7" r="1" />
          <circle cx="2" cy="11" r="1" /><circle cx="8" cy="11" r="1" />
        </svg>
        Drag to move
      </span>
      <strong :title="sessionName">{{ sessionName }}</strong><span class="companion-state" :class="{ warning: offline || muted || voiceMuted }" role="status">{{ stateLabel }}</span>
    </header>
    <!-- Left rail: the user's indicator. Lights up while they talk. -->
    <div class="rail left" :class="{ active: mode === 'user' }">
      <svg viewBox="0 0 100 100" class="hex" aria-hidden="true">
        <rect width="100" height="100" rx="24" fill="var(--surface-hover)" />
        <!-- Always drawn: silence is a slow breath, speech rides on top. -->
        <g class="spectrum">
          <rect v-for="(h, i) in bars" :key="i"
            :x="26 + i * 7.5" :y="50 - h / 2" width="4.5" :height="h"
            rx="2" />
        </g>
      </svg>
      <span>{{ muted ? "Mic off" : mode === "user" ? "Recording" : "Microphone" }}</span>
    </div>

    <!-- The thread: pixel-clamped, scrollable, pinned to the newest. -->
    <div ref="scroller" class="thread" tabindex="0" role="region" aria-label="Conversation history" @scroll.passive="onScroll" :class="{ nearscroll: nearScroll, scrollable: overflowing, 'clipped-below': clippedBelow }" :style="{ maxHeight: draggable ? undefined : threadHeight + 'px' }">
      <transition-group
        :name="animateArrival ? 'arrive' : ''"
        tag="div"
        class="msgs"
      >
        <Bubble
          v-for="(m, i) in history"
          :key="m.id ?? `pos-${i}`"
          :class="[sizeOf(m.text), { older: i < history.length - 1 || !!liveText }]"
          compact
          :side="m.role === 'claude' ? 'right' : 'left'"
          :accent="m.role === 'claude' ? 'violet' : 'amber'"
          :who="m.role === 'user' ? 'You' : sessionName" :status-kind="m.statusKind ?? 'off'" :status-label="m.statusLabel ?? ''" time=""
          :text="m.text"
        />
      </transition-group>
      <Bubble
        v-if="!composingMessages.length && mode === 'user' && liveText"
        class="livebubble"
        :class="sizeOf(liveText)"
        compact live
        side="left"
        accent="amber"
        who="" status-kind="rec" status-label="" time=""
        :text="liveText"
      />
      <span v-else-if="!composingMessages.length && mode === 'user'" class="listening">Listening…</span>
      <span v-else-if="!feed.length && !liveText && !activity" class="listening">Start talking. Your conversation will appear here.</span>

      <!-- The present: what the agent is doing between messages. -->
      <span v-if="activity" class="activity">{{ activity }}<i /><i /><i /></span>

      <!-- Below the line: still waiting its turn. -->
      <Bubble
        v-for="m in waitingShown"
        :key="`w-${m.id}`"
        class="pending"
        :class="sizeOf(m.text)"
        compact
        :side="m.role === 'claude' ? 'right' : 'left'"
        :accent="m.role === 'claude' ? 'violet' : 'amber'"
        :who="m.role === 'user' ? 'You' : sessionName" :status-kind="m.statusKind ?? 'off'" :status-label="m.statusLabel ?? ''" time=""
        :text="m.text"
      />
      <span v-if="waitingExtra" class="listening">+{{ waitingExtra }} waiting</span>

      <!-- The dashboard composer is inline at the widget thread’s bottom. -->
      <Bubble
        v-for="m in composingMessages"
        :key="`live-${m.id}`"
        class="in-flight"
        :class="sizeOf(m.text)"
        compact
        :live="m.statusKind === 'rec'"
        side="left" accent="amber" who="You" time=""
        :status-kind="m.statusKind ?? 'off'" :status-label="m.statusLabel ?? ''"
        :text="m.text"
      />

    </div>

    <!-- Drawn here, not in the rail: the rail scrolls and would clip it.
         Sits above everything so a full-screen widget still names the
         avatar under the pointer, where the pointer already is. -->
    <div v-if="tip" class="avatar-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">{{ tip.text }}</div>

    <!-- Session controls stay below the scrollable conversation. -->
    <div class="rail right" :class="{ active: mode === 'claude' }">
      <!-- Selection preserves the session order and button sizes. -->
      <button
        v-for="a in agents"
        :key="a.name"
        class="head"
        :class="{ other: !a.active, current: a.active, unread: a.unread }"
        :aria-label="conversationLabel(a.label, a.name)" :aria-pressed="!!a.active"
        @mouseenter="showTip($event, conversationLabel(a.label, a.name))" @mouseleave="tip = null"
        @focus="showTip($event, conversationLabel(a.label, a.name))" @blur="tip = null"
        @click="$emit('select', a.name)"
      ><VoiceAvatar :voice="a.voice" :size="44" :set="avatarSet" /><span v-if="a.waiting" class="waiting">{{ a.waiting > 9 ? "9+" : a.waiting }}</span></button>
      <!-- No agent list (Storybook, single conversation): just the portrait. -->
      <span v-if="!agents.length" class="head current"
      ><VoiceAvatar :voice="voice" :size="44" :set="avatarSet" /><span v-if="waiting" class="waiting">{{ waiting > 9 ? "9+" : waiting }}</span></span>
    </div>
  </div>
</template>

<style>
body.companion-transparent, body.companion-transparent #app { background:transparent; }
:is(body, div).companion-transparent .companion { background:transparent; border-color:transparent; box-shadow:none; }
/* Reveal the fixed window boundary and drag bar only when reached for. */
:is(body, div).companion-transparent .companion-window::after { content:""; position:absolute; inset:1px; border:1px solid #f3f4f5b3; border-radius:10px; box-shadow:inset 0 0 0 1px #151619cc; pointer-events:none; opacity:0; transition:opacity .15s; }
/* Invisible at rest, but NOT pointer-events:none.
 *
 * A bar that ignores the pointer cannot trigger the :hover that reveals it,
 * so approaching the widget from ABOVE - the natural way to reach a title
 * bar - left it hidden, while approaching across a bubble lit it up. Same
 * gesture, opposite result. (This is NOT what broke dragging; see the
 * drag-region note below for that.) */
:is(body, div).companion-transparent .companion-window .companion-header { opacity:0; transition:opacity .15s; }
:is(body, div).companion-transparent .companion-window:hover::after,
body.companion-transparent.hovering .companion-window::after,
:is(body, div).companion-transparent .companion-window:focus-within::after { opacity:1; }
:is(body, div).companion-transparent .companion-window:hover .companion-header,
body.companion-transparent.hovering .companion-window .companion-header,
:is(body, div).companion-transparent .companion-window:focus-within .companion-header { opacity:1; }
:is(body, div).companion-transparent .companion-window .thread { scrollbar-width:none; scrollbar-gutter:auto; mask-image:linear-gradient(transparent, black 18px); }
:is(body, div).companion-transparent .companion-window .thread::-webkit-scrollbar { display:none; }
:is(body, div).companion-transparent .companion-header,
:is(body, div).companion-transparent .rail { background:rgba(27,29,33,.94); border-radius:10px; box-shadow:0 0 0 1px #f3f4f580, 0 0 0 2px #151619b3; }
:is(body, div).companion-transparent .companion-header { padding:7px 10px; border-bottom:0; }
:is(body, div).companion-transparent .rail { padding:5px; }
:is(body, div).companion-transparent .msg { background:color-mix(in srgb, var(--message-surface) 94%, transparent); border-color:#f3f4f580; box-shadow:0 0 0 1px #151619b3; }
:is(body, div).companion-transparent .listening,
:is(body, div).companion-transparent .activity { background:rgba(27,29,33,.94); border-radius:8px; padding:6px 10px; }
/* NO-DRAG BELONGS TO THE SCROLL CONTAINER, NEVER TO WHAT SCROLLS INSIDE IT.
 *
 * Chromium builds the window's drag region from the UNCLIPPED border box of
 * every element that declares -webkit-app-region, in document order: drag
 * adds, no-drag subtracts. A message scrolled up out of the thread is still
 * laid out - above the thread, invisible, and geometrically on top of the
 * title bar - so a no-drag on .msg subtracted the bar itself, leaving a one
 * or two pixel sliver that moved with the scroll position (#63). Excluding
 * the thread's own box excludes everything in it and never overflows it.
 * Same for buttons: bubbles carry some, so only the rail's are excluded. */
:is(body, div).companion-transparent .msg, :is(body, div).companion-transparent .msg * { cursor:text; user-select:text; }
:is(body, div).companion-transparent .thread { -webkit-app-region:no-drag; }
body.companion-transparent button { cursor:pointer; }
:is(body, div).companion-transparent .rail button { -webkit-app-region:no-drag; }
:is(body, div).companion-transparent .drag-strip { -webkit-app-region:drag; }
</style>
<style scoped>
.companion { width:100%; min-width:0; max-height:100%; overflow:hidden; box-sizing:border-box; border:1px solid var(--line-strong); background:var(--panel-solid); color:var(--ink); border-radius:14px; padding:14px; font-family:var(--sans); display:flex; flex-wrap:wrap; gap:12px; align-items:center; position:relative; box-shadow:0 8px 28px #0003; }
.companion-header { display:flex; justify-content:space-between; align-items:center; gap:12px; width:100%; padding-bottom:12px; border-bottom:1px solid var(--line); order:-2; }
.companion-header strong { font-size:13px; font-weight:600; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.companion-state { flex:none; font-size:11px; color:var(--green); }
.companion-state.warning { color:var(--amber); }
.companion .companion-header.drag-strip { box-sizing:border-box; min-height:34px; gap:10px; padding:5px 8px; border:1px solid transparent; border-radius:6px; background:#202226; box-shadow:none; -webkit-app-region:drag; cursor:grab; user-select:none; }
.drag-strip strong { margin-right:auto; font-size:12px; }
/* The whole bar reads as a handle, children included - a text cursor over
   the title says "select me", which is the opposite of what it does. */
.drag-strip, .drag-strip * { cursor:grab; }
.drag-strip:active, .drag-strip:active * { cursor:grabbing; }
/* Text inside the bar must not become a selection target - a click that
   starts selecting is a click that does not drag. */
.drag-strip strong, .drag-strip .drag-hint, .drag-strip .companion-state {
  -webkit-app-region: drag; user-select: none; pointer-events: none;
}
.drag-hint { display:flex; flex:none; align-items:center; gap:5px; color:var(--muted); font-size:10px; white-space:nowrap; }
.thread { order:-1; flex-basis:100%; min-width:0; min-height:0; overflow-y:auto; display:flex; flex-direction:column; gap:10px; padding:2px 4px 2px 1px; scrollbar-gutter:stable; }
.msgs { display:flex; flex-direction:column; gap:10px; }
.thread :deep(.pending), .thread :deep(.in-flight) { border-style:dashed; }
.thread :deep(.size-l .txt) { font-size:14px; }
.thread :deep(.size-m .txt), .thread :deep(.size-s .txt) { font-size:13px; }
.rail { flex:none; }
.rail.left { display:flex; align-items:center; gap:7px; font-size:11px; color:var(--muted); }
.hex { flex:none; width:48px; height:48px; color:var(--muted); }
.spectrum rect { fill:currentColor; }
.rail.active .hex, .rail.left.active { color:var(--amber); }
.rail.right { display:flex; gap:7px; align-items:center; margin-left:auto; max-width:75%; padding:5px 4px; overflow-x:auto; scrollbar-width:none; }
.rail.right::-webkit-scrollbar { display:none; }
.head { position:relative; display:flex; flex:none; width:48px; height:48px; border:2px solid transparent; border-radius:12px; background-color:var(--surface-hover); padding:0; }
.head.current { border-color:var(--cyan); }
.head:hover { border-color:var(--ink); }
.avatar-tip {
  position:absolute; transform:translate(-50%, -100%); margin-top:-8px;
  padding:5px 9px; border-radius:8px; background:rgba(20,22,26,.97);
  box-shadow:0 0 0 1px rgba(243,244,245,.35), 0 6px 20px rgba(0,0,0,.5);
  color:#f3f4f5; font-size:12px; line-height:1; white-space:nowrap;
  pointer-events:none; z-index:50;
}
/* The title bar is showing a name you are POINTING AT, not the one you are
   in - dim it slightly so the two are never confused. */
/* Naming the hovered avatar happens in the TITLE BAR, not in a tooltip
 * beside the rail: this rail scrolls horizontally (overflow-x), which
 * clips anything drawn outside it - the leftmost avatar's tooltip had
 * nowhere to go and simply vanished. The title bar is already visible on
 * hover, already says which conversation you are in, and is the place the
 * eye is anyway. */
.head.unread { border-bottom-color:var(--amber); }
.rail.active .head.current { border-color:var(--green); }
.waiting { position:absolute; top:-5px; right:-6px; min-width:14px; height:14px; padding:0 3px; background:var(--amber); color:var(--bg0); border-radius:7px; font:600 9px/14px var(--sans); }
.listening { padding:16px 8px; color:var(--muted); font-size:13px; }
.activity { color:var(--violet); font-size:12px; overflow-wrap:anywhere; align-self:flex-end; padding:6px 10px; }
.activity i { display:inline-block; width:3px; height:3px; margin-left:3px; background:currentColor; border-radius:50%; animation:dot 1.2s infinite; }
.activity i:nth-child(2) { animation-delay:.2s; }
.activity i:nth-child(3) { animation-delay:.4s; }
.livebubble { flex:none; position:sticky; bottom:0; z-index:2; }
.arrive-enter-active { transition:opacity .18s ease, transform .18s ease; }
.arrive-enter-from { opacity:0; transform:translateY(6px); }
@keyframes dot { 50% { opacity:.4; } }
.companion.narrow { padding:8px; gap:8px; }
.companion.narrow .rail.left > span { display:none; }
</style>
