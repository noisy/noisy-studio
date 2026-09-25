<script setup lang="ts">
/** The companion (#28) wired to the live daemon.
 *
 * Served at /companion, meant to be opened as its own small window and
 * parked over the editor. The browser cannot make a window transparent or
 * pin it above other apps - that needs the native shell - but everything
 * below it is real: the same feed, the same portrait, the same rails, fed
 * by the daemon instead of Storybook fixtures.
 */
import { computed, ref } from "vue";
import { limitSettledHistory } from "../conversationCard";
import "../styles/companion-window.css";
import Companion, { type CompanionAgent } from "./Companion.vue";
import { useDaemonState } from "../composables/useDaemonState";
import { orderAgents } from "./agentOrder";
import { useConversationFeed } from "../composables/useConversationFeed";
import { useMicStream } from "../composables/useMicStream";
import { useDocumentPip } from "../composables/useDocumentPip";

/* Filter here rather than using the composable's `utterances`.
 *
 * That list is only reassigned inside the poll tick, so switching agent
 * waited up to a full poll before the thread caught up - the head changed
 * instantly, the conversation arrived a beat later. `allUtterances` already
 * holds every agent's messages in memory, so filtering it against the
 * selected agent switches in the same frame as the click. */
const { status, offline, allUtterances, character, viewedAgent, selectAgent } = useDaemonState();

const mine = computed(() =>
  allUtterances.value.filter((u) => u.agent === viewedAgent.value),
);
// Live mic level, so the spectrum follows the voice instead of looping.
const { level } = useMicStream();

// Placement differs from the dashboard composer, lifecycle semantics do not.
const { cards } = useConversationFeed(mine);
const HISTORY_CARDS_SHOWN = 12;
const feed = computed(() => limitSettledHistory(cards.value, HISTORY_CARDS_SHOWN));

/* Document Picture-in-Picture: the only way a browser gets a genuinely
 * always-on-top window. It hosts real DOM, so the live component moves into
 * it - no second render, no duplicated state. Chrome only, and only from a
 * click: browsers refuse to spawn a floating window without a user gesture.
 *
 * Styles do NOT follow the DOM into that window, so every stylesheet has to
 * be copied across by hand. Miss this and the widget arrives unstyled.
 */
// A native shell can ask for a see-through page: /companion?transparent=1
if (new URLSearchParams(window.location.search).has("transparent")) {
  document.body.classList.add("companion-transparent");
}

/* Inside the desktop app the window IS the floating widget, so the button
 * that pops one out has nothing to do - it would open a picture-in-picture
 * copy of a window that already floats. */
const nativeShell =
  typeof navigator !== "undefined" && navigator.userAgent.includes("Electron");

// Native hover comes from the shell's cursor watcher. Browser previews use
// the window element's :hover state, so hovering the backdrop reveals nothing.
const host = ref<HTMLElement | null>(null);
const anchor = ref<HTMLElement | null>(null);
const { supported: pipSupported, open: pipOpen, popOut } = useDocumentPip(host, anchor);

/* Every conversation, in the dashboard's own tab order, including offline
 * sessions. Unread marks anything waiting to be delivered there. */
const others = computed<CompanionAgent[]>(() => {
  const s = status.value;
  if (!s) return [];
  const meta = s.agents_meta ?? {};
  const queued = s.queued_by_agent ?? {};
  // Offline agents stay: a tab still open is a conversation still
  // switched to, and hiding it makes heads appear and vanish as
  // sessions idle out. Order comes from the SAME rule as the tabs.
  return orderAgents(Object.keys(s.agents ?? {}), meta)
    .map((name) => ({
      name,
      // The dashboard titles its tabs from agent_labels; the keys of the
      // agents map are SESSION IDS. Without this the widget shows a hash
      // where the dashboard shows a name - and looks correct only for an
      // agent whose id happens to be readable, like "codex".
      label: s.agent_labels?.[name] ?? "",
      voice: s.agent_voices?.[name] ?? "rex",
      active: name === viewedAgent.value,
      unread: (queued[name] ?? 0) > 0,
      waiting: queued[name] ?? 0,
    }));
});

/* What this agent is doing between messages, straight from the daemon's
 * activity line - the same source and the same freshness window the
 * dashboard uses, so the two never disagree about who is working. */
const ACTIVITY_FRESH_S = 20;
const activity = computed(() => {
  const a = status.value?.activity?.[viewedAgent.value ?? ""];
  if (!a?.text) return null;
  return Date.now() / 1000 - a.at < ACTIVITY_FRESH_S ? a.text : null;
});

const mode = computed<"claude" | "user" | "idle">(() => {
  if (status.value?.claude_speaking) return "claude";
  // Holding push-to-talk counts as having the floor even before a word is
  // spoken - the dashboard says ON AIR at that moment, and the widget has to
  // agree with it. Waiting for `recording` leaves the rail dim while the
  // user is already live.
  if (status.value?.ptt_held || status.value?.recording) return "user";
  return "idle";
});
</script>

<template>
  <div ref="anchor" class="companion-window">
    <div ref="host" class="companion-host">
      <Companion
        draggable
        :mode="mode"
        :muted="status?.muted"
        :voice-muted="status?.voice_muted || (!!viewedAgent && status?.muted_agents?.includes(viewedAgent))"
        :offline="offline"
        :voice="character?.voice ?? 'rex'"
        :feed="feed"
        :max-height="220"
        :level="level"
        :activity="activity"
        :agents="others"
        @select="selectAgent"
      />
    </div>
    <button
      v-if="pipSupported && !pipOpen && !nativeShell"
      class="pop-out"
      aria-label="Float above every window"
      title="Float above every window"
      @click="popOut"
    >
      ↗
    </button>
  </div>
</template>

<style>
/* Transparent-mode styling lives in Companion.vue, next to the component
   it dresses, so Storybook can show it too. */
html,
body,
#app {
  margin: 0;
  height: 100%;
}
</style>

<style scoped>
/* Everything ABOVE the title bar's lower edge drags the window.
 *
 * The bar does not touch the window's top edge - the window has its own
 * padding - so there was a strip of dead pixels exactly where a hand
 * naturally goes when reaching for a title bar. This covers the bar and
 * everything above it, so the whole top band behaves as one handle, with
 * the grab cursor to say so. Elements below (thread, rail) declare
 * no-drag for themselves. */
.companion-window::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  /* window padding (8) + bar height (34) + a hair, so the region ends ON
     the bar's lower edge rather than short of it. */
  height: 43px;
  -webkit-app-region: drag;
  cursor: grab;
  z-index: 1;
}
.companion-window:active::before { cursor: grabbing; }

/* Reserve space beside the microphone for the browser-only PiP control. */
.companion-window:has(.pop-out) :deep(.rail.right) { max-width:calc(100% - 80px); }
.pop-out {
  position: absolute;
  bottom: 30px;
  left: 60px;
  z-index: 201;
  padding: 0;
  width: 24px;
  height: 24px;
  font: inherit;
  font-size: 16px;
  letter-spacing: normal;
  text-transform: none;
  color: var(--ink);
  background: #202226;
  border: 1px solid var(--muted);
  border-radius: 4px;
  cursor: pointer;
  -webkit-app-region: no-drag;
}
.pop-out:hover {
  color: #fff;
  border-color: rgba(148, 163, 220, 0.7);
}
</style>
