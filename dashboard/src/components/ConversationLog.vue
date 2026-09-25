<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useConversationFeed } from "../composables/useConversationFeed";
import type { Utterance } from "../types";
import ActivityLine from "./ActivityLine.vue";
import FeedRow from "./FeedRow.vue";
import UserBubble from "./UserBubble.vue";

const props = withDefaults(
  defineProps<{
    utterances: Utterance[];
    historyTrimmed?: boolean;
    /** speaker -> palette color, straight from status.speaker_colors. */
    speakerColors?: Record<string, string>;
    /** speaker -> free bubble title, straight from status.speaker_labels. */
    speakerLabels?: Record<string, string>;
    playingId?: number;
    playbackPaused?: boolean;
    activity?: { text: string; at: number } | null;
  }>(),
  { playingId: 0, playbackPaused: false, activity: null, historyTrimmed: false },
);
defineEmits<{
  replay: [utterance: Utterance];
  cancel: [utterance: Utterance];
  pause: [utterance: Utterance];
  skip: [utterance: Utterance];
}>();

// One feed logic for every surface - see useConversationFeed.ts. The
// widget consumes the same composable; only styling may differ.
const utterancesRef = computed(() => props.utterances);
const { ordered, liveTail, settled, processed, pending } =
  useConversationFeed(utterancesRef);

// The card being spoken renders right above the busy line — quoting the
// speech in the line too would double it (see ActivityLine).
const playingCardVisible = computed(
  () => props.playingId !== 0 && settled.value.some((u) => u.id === props.playingId),
);

const feed = ref<HTMLElement | null>(null);
const slot = ref<HTMLElement | null>(null);

// The composer floats OVER the feed's bottom padding instead of owning a
// dead strip below it: while you scroll, history flows through that area;
// only at the very bottom does the padding hold space for the overlay —
// and it grows with the bubble as live transcription lengthens it.
const SLOT_MIN_PX = 96; // one single-line bubble
const padBottom = ref(SLOT_MIN_PX);
let resizeObserver: ResizeObserver | undefined;
onMounted(() => {
  if (typeof ResizeObserver !== "undefined" && slot.value) {
    resizeObserver = new ResizeObserver(() => {
      padBottom.value = Math.max(SLOT_MIN_PX, slot.value?.offsetHeight ?? 0);
    });
    resizeObserver.observe(slot.value);
  }
});
onUnmounted(() => resizeObserver?.disconnect());

function scrollToBottom() {
  if (feed.value) feed.value.scrollTop = feed.value.scrollHeight;
}

// Sticky-bottom, like every decent chat: we follow new content ONLY while
// you are at the bottom. Scrolled up to read something older? Nothing may
// move your view — new messages just light up the jump-down button.
const STICK_THRESHOLD_PX = 24;
const stickToBottom = ref(true);
function onFeedScroll() {
  const el = feed.value;
  if (!el) return;
  stickToBottom.value = el.scrollTop + el.clientHeight >= el.scrollHeight - STICK_THRESHOLD_PX;
}
function jumpToBottom() {
  stickToBottom.value = true;
  scrollToBottom();
}

// Scrolled to the newest message by default, and kept there as new ones
// land — but only while sticking.
onMounted(scrollToBottom);
watch(
  () => {
    const last = ordered.value[ordered.value.length - 1];
    // The busy row appearing/changing also grows the feed's bottom.
    return `${last ? `${last.id}:${last.updated_at}` : ""}|${props.activity?.text ?? ""}`;
  },
  async () => {
    await nextTick();
    if (stickToBottom.value) scrollToBottom();
  },
);
</script>

<template>
  <div class="logroot">
    <div ref="feed" class="feed" tabindex="0" role="region" aria-label="Conversation history" :style="{ paddingBottom: padBottom + 'px' }" @scroll="onFeedScroll">
      <p v-if="historyTrimmed" class="history-trimmed" role="note">Older messages are no longer kept. Showing recent history.</p>
      <FeedRow
        v-for="utterance in processed"
        :tint="(speakerColors?.[utterance.speaker ?? ''] as 'normal'|'green'|'purple'|'red') ?? 'green'"
        :label="speakerLabels?.[utterance.speaker ?? ''] ?? ''"
        :key="utterance.id"
        :utterance="utterance"
        :playing="utterance.id === playingId"
        :paused="playbackPaused"
        @replay="$emit('replay', $event)"
        @cancel="$emit('cancel', $event)"
        @pause="$emit('pause', $event)"
        @skip="$emit('skip', $event)"
      />
      <!-- The processed line: everything above already happened, everything
           below still waits its turn. -->
      <ActivityLine :activity="activity" :playing-card-visible="playingCardVisible" />
      <FeedRow
        v-for="utterance in pending"
        :tint="(speakerColors?.[utterance.speaker ?? ''] as 'normal'|'green'|'purple'|'red') ?? 'green'"
        :label="speakerLabels?.[utterance.speaker ?? ''] ?? ''"
        :key="utterance.id"
        :utterance="utterance"
        :playing="utterance.id === playingId"
        @replay="$emit('replay', $event)"
        @cancel="$emit('cancel', $event)"
      />
      <p v-if="!ordered.length && !historyTrimmed" class="empty">Start a conversation</p>
    </div>
    <button
      v-if="!stickToBottom"
      class="jumpdown"
      :style="{ bottom: padBottom + 10 + 'px' }"
      title="Jump to the newest message and follow"
      @click="jumpToBottom"
    >▼</button>
    <div ref="slot" class="liveslot">
      <UserBubble v-if="liveTail" :utterance="liveTail" />
    </div>
  </div>
</template>

<style scoped>
.logroot {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.feed {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--line-strong) transparent;
  padding-right: 4px;
}
.history-trimmed {
  text-align: center;
  color: var(--muted);
  font-size: 11px;
  margin: 8px 0 16px;
}
.empty {
  color: var(--muted);
  font-size: 16px;
  letter-spacing: normal;
  text-align: center;
  padding: 72px 12px;
}
.liveslot {
  position: absolute;
  left: 0;
  right: 4px;
  bottom: 0;
  display: flex;
  flex-direction: column;
}
.jumpdown {
  position: absolute;
  right: 28px;
  z-index: 1;
  width: 28px;
  height: 28px;
  font-family: var(--sans);
  font-size: 11px;
  color: var(--cyan);
  background: var(--bg1);
  border: 1px solid var(--line-strong);
  cursor: pointer;
  border-radius: 8px;
}
.jumpdown:hover { color: var(--cyan-hi); border-color: var(--cyan); text-shadow: none; }

.liveslot :deep(.msg) {
  background-color: var(--bg1);
}
</style>
