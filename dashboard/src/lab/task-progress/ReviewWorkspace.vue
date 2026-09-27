<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import App from "../../App.vue";
import VoiceAvatar from "../../components/VoiceAvatar.vue";
import { conversations, counts } from "./fixtures";
import type { Work } from "./fixtures";
const props = withDefaults(
  defineProps<{
    placement?: "strip" | "floating" | "dock";
    unavailable?: boolean;
  }>(),
  { placement: "floating", unavailable: false },
);
const root = ref<HTMLElement | null>(null),
  target = ref<HTMLElement | null>(null),
  dialog = ref<HTMLDialogElement | null>(null);
const selected = ref<Work>(conversations[2]!);
const mode = ref<"auto" | "ptt">("ptt");
const holding = ref(false),
  feedback = ref(false),
  confirming = ref(false),
  approved = ref(false);
const position = ref({ x: 32, y: 110 });
const dragging = ref<{ x: number; y: number } | null>(null);
const widgetStyle = computed(() =>
  props.placement === "floating"
    ? { left: position.value.x + "px", top: position.value.y + "px" }
    : {},
);
const preview = `<!doctype html><html lang="en"><meta name="viewport" content="width=device-width"><style>body{margin:0;background:#172322;color:#ecebe3;font:16px system-ui;padding:65px 8%;text-align:center}small{letter-spacing:3px;color:#9eb9ac}h1{font:54px Georgia;margin:25px 0}p{color:#b5c6ba}.crew{display:flex;justify-content:center;gap:28px;margin:75px 0}.person{width:130px;padding:35px 12px;border:1px solid #64776a;border-radius:60px 60px 15px 15px;background:#233732}.person b{display:block;font:40px Georgia;color:#c6d7aa;margin-bottom:18px}.person span{font-size:12px}footer{margin-top:70px;font:22px Georgia;color:#c6d7aa}
.floating .review-widget { max-height: calc(100dvh - 90px); overflow: auto; }
</style><small>NOISY STUDIO · FICTIONAL REVIEW ARTIFACT</small><h1>A company of characters.</h1><p>Shared ambition. A whole crew of different minds.</p><div class="crew"><div class="person"><b>M</b>Mira<br><span>Design lead</span></div><div class="person"><b>R</b>Rook<br><span>Quality</span></div><div class="person"><b>L</b>Lux<br><span>Engineering</span></div></div><footer>“The team has opinions. That’s why it works.”</footer></html>`;
onMounted(async () => {
  await nextTick();
  const rail = root.value?.querySelector(".col-left");
  if (!rail) return;
  const host = document.createElement("div");
  rail.insertBefore(host, rail.lastElementChild);
  target.value = host;
});
onBeforeUnmount(() => target.value?.remove());
function open(work: Work) {
  selected.value = work;
  feedback.value = false;
  approved.value = false;
  confirming.value = false;
  dialog.value?.showModal();
}
function close() {
  holding.value = false;
  confirming.value = false;
  dialog.value?.close();
}
function startDrag(event: PointerEvent) {
  if (props.placement !== "floating") return;
  dragging.value = {
    x: event.clientX - position.value.x,
    y: event.clientY - position.value.y,
  };
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
}
function move(event: PointerEvent) {
  if (!dragging.value) return;
  position.value = {
    x: Math.max(
      8,
      Math.min(window.innerWidth - 350, event.clientX - dragging.value.x),
    ),
    y: Math.max(
      70,
      Math.min(window.innerHeight - 320, event.clientY - dragging.value.y),
    ),
  };
}
function place(side: string) {
  position.value = {
    x: side === "left" ? 16 : Math.max(16, window.innerWidth - 370),
    y: 90,
  };
}
function release() {
  if (holding.value) {
    holding.value = false;
    feedback.value = true;
  }
}
</script>
<template>
  <div ref="root" class="task-review-lab">
    <App /><Teleport v-if="target" :to="target"
      ><section class="thin-tasks">
        <header>
          <h2>Tasks <small>demo</small></h2>
          <span>1 ready</span>
        </header>
        <div v-for="work in conversations" :key="work.id" class="thin-row">
          <span :title="work.topic">{{ work.name }}</span>
          <div
            class="thin-track"
            :aria-label="
              work.tasks
                ? `${counts(work).done} of ${counts(work).total} tasks complete`
                : 'No task information'
            "
          >
            <i
              v-if="work.tasks?.length"
              :style="{
                width: (counts(work).done / counts(work).total) * 100 + '%',
              }"
            /><span v-else>no task info</span>
          </div>
          <button v-if="work.review" @click="open(work)">
            {{ work.visited ? "Revisit" : "Review" }} ↗</button
          ><small v-else>{{
            work.state === "done"
              ? "Done"
              : work.state === "unknown"
                ? "—"
                : "Working"
          }}</small>
        </div>
        <footer>Task steps, not time estimates.</footer>
      </section></Teleport
    >
    <dialog
      ref="dialog"
      class="review-dialog"
      :class="placement"
      @cancel="holding = false"
    >
      <header class="review-header">
        <button @click="close">← Back to dashboard</button>
        <div>
          <strong>{{ selected.topic }}</strong
          ><small>Review workspace · demo</small>
        </div>
        <a
          :href="selected.review?.url"
          target="_blank"
          rel="noopener noreferrer"
          >Open externally ↗</a
        >
      </header>
      <section class="artifact">
        <div v-if="unavailable" class="embed-fallback">
          <h2>This page cannot be shown here.</h2>
          <p>
            Some sites require a separate browser tab. Your review controls stay
            available in Noisy Studio.
          </p>
          <a
            :href="selected.review?.url"
            target="_blank"
            rel="noopener noreferrer"
            >Open review in a new tab ↗</a
          ><small>Demo of an embedding restriction; no policy bypass.</small>
        </div>
        <iframe
          v-else
          title="Synthetic design under review"
          sandbox=""
          :srcdoc="preview"
        />
      </section>
      <aside
        class="review-widget"
        :style="widgetStyle"
        aria-label="Review conversation"
      >
        <div
          class="widget-handle"
          @pointerdown="startDrag"
          @pointermove="move"
          @pointerup="dragging = null"
          @pointercancel="dragging = null"
        >
          <span>{{
            placement === "floating"
              ? "⠿ Drag review controls"
              : "Review with your agent"
          }}</span
          ><small>IN-APP · DEMO</small>
        </div>
        <div class="review-person">
          <VoiceAvatar
            :voice="selected.id === 'nova' ? 'eve' : 'ara'"
            :size="42"
            set="editorial"
          />
          <div>
            <strong>{{ selected.name }}</strong
            ><small>Feedback recipient · {{ selected.topic }}</small>
          </div>
        </div>
        <div class="mode">
          <button
            :aria-pressed="mode === 'ptt'"
            @click="
              mode = 'ptt';
              holding = false;
            "
          >
            Push to talk</button
          ><button
            :aria-pressed="mode === 'auto'"
            @click="
              mode = 'auto';
              holding = false;
            "
          >
            Auto
          </button>
        </div>
        <button
          v-if="mode === 'ptt'"
          class="talk"
          @pointerdown="
            holding = true;
            ($event.currentTarget as HTMLElement).setPointerCapture(
              $event.pointerId,
            );
          "
          @pointerup="release"
          @pointercancel="holding = false"
          @keydown.space.prevent="holding = true"
          @keyup.space.prevent="release"
          @blur="holding = false"
        >
          {{
            holding
              ? "Recording to " + selected.name + "… (demo)"
              : "Hold to talk to " + selected.name
          }}
        </button>
        <div v-else class="auto-note">
          ● Auto · listening to {{ selected.name }}
          <small>Preview only · microphone is off</small
          ><button @click="feedback = true">Simulate spoken feedback</button>
        </div>
        <p class="privacy">
          No microphone or messages connected in this prototype.
        </p>
        <div v-if="feedback" class="feedback">
          <small>YOU → {{ selected.name }} · SAMPLE TRANSCRIPT</small>
          <p>
            “I like this direction. Could you make the labels a little larger?”
          </p>
          <span>Feedback preview · not sent</span>
        </div>
        <div v-if="approved" class="approved">
          ✓ Approved in this demo
          <button @click="approved = false">Undo</button>
        </div>
        <div v-else-if="confirming" class="confirm">
          <strong>Approve {{ selected.topic }}?</strong>
          <p>
            This marks the result approved, separately from sending feedback.
          </p>
          <button
            @click="
              approved = true;
              confirming = false;
            "
          >
            Yes, approve result</button
          ><button @click="confirming = false">Keep reviewing</button>
        </div>
        <button v-else class="approve" @click="confirming = true">
          Approve result…
        </button>
        <div v-if="placement === 'floating'" class="position">
          <span>Move controls</span><button @click="place('left')">Left</button
          ><button @click="place('right')">Right</button>
        </div>
      </aside>
    </dialog>
  </div>
</template>
<style scoped>
.thin-tasks {
  padding: 8px 12px;
  border: 1px solid var(--line, #363a43);
  border-radius: 8px;
  color: var(--ink, #e4e7ee);
  background: var(--panel, #202329);
  font: 11px var(--sans, system-ui);
}
.thin-tasks header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.thin-tasks h2 {
  font-size: 11px;
  margin: 0;
}
.thin-tasks h2 small,
.thin-tasks header > span {
  font-size: 9px;
  color: var(--muted, #9ba5b5);
  font-weight: 400;
}
.thin-row {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 55px;
  gap: 7px;
  align-items: center;
  height: 25px;
}
.thin-track {
  height: 3px;
  background: #77839b33;
  border-radius: 2px;
  position: relative;
}
.thin-track i {
  display: block;
  background: var(--brand-accent, #a8c8ef);
  height: 100%;
  border-radius: 2px;
}
.thin-track > span {
  position: absolute;
  top: -6px;
  background: var(--panel, #202329);
  font-size: 8px;
  color: var(--muted, #9ba5b5);
}
.thin-row button {
  padding: 2px 0;
  border: 0;
  background: none;
  color: var(--brand-accent, #a8c8ef);
  font: inherit;
  font-size: 9px;
  cursor: pointer;
  text-align: right;
}
.thin-row small {
  font-size: 8px;
  color: var(--muted, #9ba5b5);
  text-align: right;
}
.thin-tasks footer {
  font-size: 8px;
  color: var(--muted, #9ba5b5);
  margin-top: 7px;
}
.review-dialog {
  width: 100vw;
  height: 100dvh;
  max-width: none;
  max-height: none;
  padding: 0;
  border: 0;
  margin: 0;
  background: #171b20;
  color: #e4e7ee;
  font: 13px var(--sans, system-ui);
}
.review-header {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 25px;
  padding: 0 20px;
  border-bottom: 1px solid #39404b;
  box-sizing: border-box;
}
.review-header div {
  flex: 1;
}
.review-header small {
  display: block;
  color: #9ca8b8;
  font-size: 10px;
  margin-top: 4px;
}
.review-header a {
  color: #bed2f0;
  font-size: 12px;
}
.review-dialog button {
  font: inherit;
  color: inherit;
  background: #2b3441;
  border: 1px solid #506076;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
}
.artifact {
  height: calc(100% - 64px);
}
iframe {
  width: 100%;
  height: 100%;
  border: 0;
  background: #172322;
}
.review-widget {
  width: 340px;
  box-sizing: border-box;
  background: #202731f5;
  border: 1px solid #65778d;
  border-radius: 12px;
  box-shadow: 0 12px 50px #0005;
  position: absolute;
  padding: 12px;
  z-index: 2;
}
.widget-handle {
  display: flex;
  justify-content: space-between;
  touch-action: none;
  color: #aebace;
  font-size: 10px;
  gap: 10px;
  padding: 0 0 12px;
  cursor: grab;
}
.widget-handle small {
  font-size: 8px;
}
.review-person {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}
.review-person strong {
  font-size: 14px;
}
.review-person small {
  display: block;
  font-size: 10px;
  margin-top: 4px;
  color: #acb8c8;
}
.mode {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}
.mode button {
  flex: 1;
  font-size: 11px;
  padding: 6px;
}
.mode button[aria-pressed="true"] {
  background: #bad3f02b;
  border-color: #b7cae8;
}
.talk,
.approve {
  width: 100%;
}
.talk {
  background: #b7cae8 !important;
  color: #14202e !important;
  font-weight: 600 !important;
  touch-action: none;
}
.privacy {
  font-size: 9px;
  color: #adb9c8;
  margin: 9px 0 14px;
}
.approve {
  margin-top: 8px;
}
.position {
  display: flex;
  align-items: center;
  gap: 6px;
  border-top: 1px solid #4e596733;
  padding-top: 9px;
  margin-top: 12px;
  font-size: 10px;
  color: #aebaca;
}
.position span {
  flex: 1;
}
.position button {
  padding: 3px 10px;
  font-size: 10px;
}
.auto-note {
  color: #c0dcbf;
  padding: 8px;
  border: 1px solid #7fa082;
  border-radius: 7px;
  font-size: 12px;
}
.auto-note small {
  display: block;
  margin: 6px 0 10px;
  color: #adb9c8;
  font-size: 9px;
}
.auto-note button {
  font-size: 10px;
}
.feedback {
  border-left: 2px solid #a5c4eb;
  padding: 8px 10px;
  background: #a5c4eb0b;
  margin: 10px 0;
}
.feedback small,
.feedback span {
  font-size: 8px;
  color: #acbed4;
}
.feedback p {
  font-size: 12px;
  line-height: 1.5;
  margin: 7px 0;
}
.confirm {
  background: #a5c4eb10;
  padding: 12px;
  border-radius: 8px;
}
.confirm p {
  font-size: 11px;
  color: #bcc9d9;
  line-height: 1.5;
}
.confirm button {
  font-size: 11px;
  margin: 4px 4px 0 0;
}
.approved {
  color: #b7dbb9;
  padding: 12px 0;
}
.approved button {
  float: right;
  font-size: 10px;
}
.dock .review-widget {
  right: 18px;
  top: 82px;
  bottom: 18px;
  overflow: auto;
}
.dock .artifact {
  margin-right: 375px;
}
.strip .review-widget {
  top: 64px;
  left: 0;
  width: 100%;
  border-radius: 0;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  padding: 12px 20px;
  box-shadow: none;
}
.strip .widget-handle,
.strip .privacy {
  display: none;
}
.strip .review-person {
  margin: 0;
  min-width: 210px;
}
.strip .mode {
  margin: 0;
}
.strip .mode button {
  white-space: nowrap;
}
.strip .talk,
.strip .approve {
  width: auto;
  margin: 0;
}
.strip .artifact {
  padding-top: 106px;
  box-sizing: border-box;
}
.strip .feedback {
  max-width: 330px;
  margin: 0;
}
.strip .confirm {
  max-width: 340px;
}
.embed-fallback {
  max-width: 470px;
  margin: auto;
  padding: 100px 25px;
  text-align: center;
}
.embed-fallback p {
  line-height: 1.6;
  color: #acb8c8;
}
.embed-fallback a {
  color: #b7cae8;
}
.embed-fallback small {
  display: block;
  margin-top: 25px;
  color: #acb8c8;
}
button:focus-visible,
a:focus-visible {
  outline: 2px solid #b7d4ff;
  outline-offset: 3px;
}
@media (max-width: 600px) {
  .review-header {
    gap: 10px;
    padding: 8px;
    height: 80px;
  }
  .review-header button,
  .review-header a {
    font-size: 10px;
  }
  .review-widget {
    width: min(340px, calc(100vw - 16px));
  }
  .dock .artifact {
    margin-right: 0;
  }
  .dock .review-widget {
    top: auto;
    bottom: 8px;
    right: 8px;
    max-height: 70vh;
  }
  .strip .artifact {
    padding-top: 200px;
  }
  .strip .review-person {
    min-width: 180px;
  }
}

.floating .review-widget {
  max-height: calc(100dvh - 90px);
  overflow: auto;
}
</style>
