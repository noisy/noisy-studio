<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onBeforeUnmount,
  ref,
  watch,
} from "vue";
import type { DaemonStatus, Utterance } from "../../types";
import { conversationLabel } from "../../conversationLabel";
import { reviewTask, setActiveAgent, setSettings } from "../../api/client";
import VoiceAvatar from "../VoiceAvatar.vue";
import { reviewUrl } from "./types";
import type { ReviewTarget } from "./types";
const props = defineProps<{
  target: ReviewTarget;
  status: DaemonStatus | null;
  offline: boolean;
  utterances: Utterance[];
}>();
const emit = defineEmits<{
  close: [];
  reviewed: [];
  startPtt: [];
  stopPtt: [];
}>();
const dialog = ref<HTMLDialogElement | null>(null),
  confirmation = ref<HTMLDialogElement | null>(null);
const error = ref(""),
  connecting = ref(false),
  selected = ref(false),
  busy = ref(false),
  transcript = ref(false);
const approval = ref(props.target.task.review_state === "approved");
const afterId = Math.max(0, ...props.utterances.map((u) => u.id));
let disposed = false;
const title = computed(() =>
  conversationLabel(
    props.status?.agent_labels[props.target.agent],
    props.target.agent,
  ),
);
const voice = computed(
  () => props.status?.agent_voices?.[props.target.agent] ?? "ara",
);
const url = computed(() => reviewUrl(props.target.task));
const matched = computed(
  () =>
    selected.value &&
    !connecting.value &&
    !props.offline &&
    props.status?.active_agent === props.target.agent,
);
const canTalk = computed(
  () =>
    matched.value &&
    !props.status?.muted &&
    props.status?.detection_mode === "ptt",
);
const messages = computed(() =>
  props.utterances.filter(
    (u) =>
      u.agent === props.target.agent &&
      u.id > afterId &&
      ["user", "claude"].includes(u.role),
  ),
);
const latest = computed(() => messages.value.at(-1));
async function connect() {
  if (connecting.value) return;
  emit("stopPtt");
  selected.value = false;
  error.value = "";
  if (props.status?.recording || props.status?.ptt_held) {
    error.value = "Finish the current recording, then reconnect this review.";
    return;
  }
  connecting.value = true;
  try {
    const active = await setActiveAgent(props.target.agent);
    if (disposed) return;
    if (active !== props.target.agent)
      throw new Error("The review conversation could not be selected.");
    selected.value = true;
    await reviewTask(
      props.target.agent,
      props.target.task.report.task_id,
      props.target.task.report.revision,
      "opened",
    );
    if (!disposed) emit("reviewed");
  } catch (reason) {
    if (!disposed)
      error.value =
        reason instanceof Error ? reason.message : "Could not open review";
  } finally {
    if (!disposed) connecting.value = false;
  }
}
function stop() {
  emit("stopPtt");
}
function close() {
  stop();
  confirmation.value?.close();
  dialog.value?.close();
  emit("close");
}
function hold(event?: PointerEvent) {
  if (!canTalk.value) return;
  if (event)
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  emit("startPtt");
}
async function changeMode(event: Event) {
  stop();
  try {
    await setSettings({
      detection_mode: (event.target as HTMLSelectElement).value as
        | "auto"
        | "ptt",
    });
  } catch {
    error.value = "The turn detection mode could not be changed.";
  }
}
async function approve(action: "approve" | "undo") {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await reviewTask(
      props.target.agent,
      props.target.task.report.task_id,
      props.target.task.report.revision,
      action,
    );
    if (disposed) return;
    approval.value = action === "approve";
    confirmation.value?.close();
    emit("reviewed");
  } catch (reason) {
    if (!disposed)
      error.value =
        reason instanceof Error ? reason.message : "Review could not be saved";
  } finally {
    if (!disposed) busy.value = false;
  }
}
function hidden() {
  if (document.hidden) stop();
}
watch(canTalk, (ready) => {
  if (!ready) stop();
});
onMounted(async () => {
  await nextTick();
  dialog.value?.showModal();
  window.addEventListener("blur", stop);
  document.addEventListener("visibilitychange", hidden);
  void connect();
});
onBeforeUnmount(() => {
  disposed = true;
  stop();
  window.removeEventListener("blur", stop);
  document.removeEventListener("visibilitychange", hidden);
  dialog.value?.close();
});
</script>
<template>
  <dialog ref="dialog" class="task-review" @cancel.prevent="close">
    <header>
      <button
        aria-label="Back to dashboard"
        title="Back to dashboard"
        @click="close"
      >
        ←
      </button>
      <div class="recipient">
        <VoiceAvatar :voice="voice" :size="32" />
        <div>
          <strong>{{ title }}</strong
          ><small>Feedback recipient</small>
        </div>
      </div>
      <div class="feedback" aria-live="polite">
        <small>{{ latest?.role === "user" ? "YOU → " + title : title }}</small>
        <p>{{ latest?.text ?? "Review " + target.task.report.title + "." }}</p>
        <button
          aria-label="Expand feedback transcript"
          title="Expand feedback transcript"
          :aria-expanded="transcript"
          @click="transcript = !transcript"
        >
          ⌄
        </button>
      </div>
      <div class="voice-controls">
        <select
          :value="status?.detection_mode"
          aria-label="Turn detection mode"
          :disabled="!matched"
          @change="changeMode"
        >
          <option value="ptt">Push to talk</option>
          <option value="auto">Auto</option></select
        ><button
          v-if="status?.detection_mode === 'ptt'"
          class="talk"
          :disabled="!canTalk"
          @pointerdown="hold"
          @pointerup="stop"
          @pointercancel="stop"
          @keydown.space.stop.prevent="hold()"
          @keyup.space.stop.prevent="stop"
          @blur="stop"
        >
          {{ status?.ptt_held ? "Recording…" : "Hold for feedback" }}</button
        ><span v-else class="listening">{{
          matched && !status?.muted
            ? "● Listening to " + title
            : status?.muted
              ? "Microphone muted"
              : "Recipient not connected"
        }}</span>
      </div>
      <button
        v-if="!approval"
        class="approve"
        :disabled="offline || busy || target.task.report.state !== 'done'"
        @click="
          stop();
          confirmation?.showModal();
        "
      >
        Approve…</button
      ><button
        v-else
        class="approve"
        :disabled="offline || busy"
        @click="approve('undo')"
      >
        ✓ Approved · Undo</button
      ><a
        v-if="url"
        :href="url"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Open review externally"
        title="Open review externally"
        >↗</a
      >
    </header>
    <div v-if="error || !matched || status?.muted" class="notice" role="status">
      {{
        error ||
        (connecting
          ? "Connecting to " + title + "…"
          : status?.muted
            ? "Microphone is muted. Unmute it on the dashboard to give spoken feedback."
            : "Feedback recipient changed or disconnected.")
      }}
      <button v-if="!matched && !connecting" @click="connect">
        Reconnect {{ title }}
      </button>
    </div>
    <aside v-if="transcript" class="transcript">
      <div>
        <strong>Review conversation</strong
        ><button aria-label="Close transcript" @click="transcript = false">
          ✕
        </button>
      </div>
      <p v-if="!messages.length">
        Spoken feedback and replies will appear here.
      </p>
      <p v-for="message in messages" :key="message.id">
        <b>{{ message.role === "user" ? "You" : title }}:</b> {{ message.text }}
      </p>
    </aside>
    <main>
      <iframe
        v-if="url"
        :src="url"
        title="Review artifact"
        sandbox="allow-scripts allow-forms"
        referrerpolicy="no-referrer"
      />
      <p v-else>There is no supported review URL.</p>
      <a
        v-if="url"
        class="fallback"
        :href="url"
        target="_blank"
        rel="noopener noreferrer"
        >Preview not loading? Open in a new tab ↗</a
      >
    </main>
    <dialog
      ref="confirmation"
      class="confirmation"
      aria-labelledby="approval-title"
    >
      <h2 id="approval-title">Approve this result?</h2>
      <p>{{ target.task.report.title }}</p>
      <small
        >This records your approval for {{ title }}. Opening a result or giving
        feedback does not approve it.</small
      >
      <p v-if="error" role="alert">{{ error }}</p>
      <div>
        <button :disabled="busy" @click="confirmation?.close()">
          Keep reviewing</button
        ><button :disabled="busy" @click="approve('approve')">
          {{ busy ? "Saving…" : "Yes, approve result" }}
        </button>
      </div>
    </dialog>
  </dialog>
</template>
<style scoped>
.task-review {
  width: 100vw;
  height: 100dvh;
  max-width: none;
  max-height: none;
  padding: 0;
  border: 0;
  margin: 0;
  background: var(--bg0, #171b20);
  color: var(--ink, #e4e7ee);
  font: 12px var(--sans, system-ui);
}
header {
  height: 88px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line, #39404b);
  box-sizing: border-box;
  background: var(--panel, #202731);
}
button,
select {
  font: inherit;
  color: inherit;
  background: var(--panel, #2b3441);
  border: 1px solid var(--line, #506076);
  border-radius: 5px;
  padding: 7px 9px;
  cursor: pointer;
}
button:disabled,
select:disabled {
  opacity: 0.5;
  cursor: default;
}
.recipient {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 170px;
  min-width: 0;
  flex-shrink: 0;
}
.recipient > div {
  min-width: 0;
}
.recipient strong {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 11px;
}
.recipient small {
  display: block;
  margin-top: 4px;
  font-size: 8px;
  color: var(--muted, #aab8cc);
}
.feedback {
  flex: 1;
  min-width: 100px;
  padding: 7px 30px 7px 10px;
  background: #a5c4eb0b;
  border-left: 2px solid var(--brand-accent, #a5c4eb);
  max-height: 60px;
  box-sizing: border-box;
  position: relative;
}
.feedback small {
  font-size: 8px;
  color: var(--muted, #aab8cc);
}
.feedback p {
  font-size: 10px;
  line-height: 14px;
  margin: 3px 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.feedback button {
  position: absolute;
  right: 5px;
  top: 17px;
  border: 0;
  background: none;
  padding: 0;
  font-size: 17px;
}
.voice-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}
.voice-controls select {
  font-size: 10px;
  padding: 7px 4px;
  width: 91px;
}
.talk {
  background: var(--brand-accent, #b7cae8);
  color: #14202e;
  font-size: 10px;
  white-space: nowrap;
  touch-action: none;
}
.listening {
  font-size: 10px;
  max-width: 150px;
}
.approve {
  font-size: 10px;
  white-space: nowrap;
}
header > a {
  color: var(--brand-accent, #c6d9f6);
  font-size: 22px;
  text-decoration: none;
  padding: 6px;
}
main {
  height: calc(100% - 88px);
  position: relative;
}
iframe {
  width: 100%;
  height: 100%;
  border: 0;
}
.fallback {
  position: absolute;
  bottom: 12px;
  left: 12px;
  padding: 6px 10px;
  background: var(--panel, #202731);
  color: var(--brand-accent, #c6d9f6);
  border-radius: 5px;
  font-size: 10px;
}
.notice {
  position: absolute;
  top: 90px;
  left: 14px;
  right: 14px;
  z-index: 2;
  padding: 10px;
  background: var(--panel, #202731);
  border: 1px solid var(--warning, #d9ad73);
  border-radius: 6px;
  font-size: 11px;
}
.notice button {
  font-size: 10px;
}
.transcript {
  position: absolute;
  right: 22px;
  top: 98px;
  width: min(440px, calc(100vw - 44px));
  max-height: 240px;
  overflow: auto;
  box-sizing: border-box;
  padding: 16px;
  background: var(--panel, #242e3c);
  border: 1px solid var(--line, #738298);
  border-radius: 9px;
  z-index: 3;
  box-shadow: 0 8px 35px #0005;
}
.transcript > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.transcript p {
  font-size: 12px;
  line-height: 1.6;
}
.transcript button {
  padding: 3px 7px;
}
.confirmation {
  background: var(--panel, #242e3c);
  color: inherit;
  border: 1px solid var(--line, #8497ad);
  border-radius: 12px;
  padding: 25px;
  max-width: 410px;
}
.confirmation::backdrop {
  background: #0008;
}
.confirmation small {
  font-size: 11px;
  line-height: 1.6;
}
.confirmation > div {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}
.confirmation button {
  font-size: 11px;
}
button:focus-visible,
select:focus-visible,
a:focus-visible {
  outline: 2px solid var(--brand-accent, #b7d4ff);
  outline-offset: 3px;
}
@media (max-width: 1000px) {
  header {
    height: 128px;
    flex-wrap: wrap;
    gap: 6px;
  }
  .recipient {
    width: calc(100% - 100px);
  }
  .feedback {
    order: 5;
  }
  .voice-controls {
    order: 6;
  }
  .approve {
    order: 7;
  }
  main {
    height: calc(100% - 128px);
  }
  .notice,
  .transcript {
    top: 138px;
  }
}
</style>
