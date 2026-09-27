<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import App from "../../App.vue";
import VoiceAvatar from "../../components/VoiceAvatar.vue";
import { reviewThreads } from "./reviewFixtures";
import type { ReviewItem, ReviewThread } from "./reviewFixtures";
withDefaults(
  defineProps<{
    header?: "inline" | "ribbon" | "companion";
    unavailable?: boolean;
  }>(),
  { header: "inline", unavailable: false },
);
const root = ref<HTMLElement | null>(null),
  target = ref<HTMLElement | null>(null),
  dialog = ref<HTMLDialogElement | null>(null),
  approvalDialog = ref<HTMLDialogElement | null>(null);
const thread = ref(reviewThreads[0]!),
  item = ref(reviewThreads[0]!.items[0]!);
const mode = ref<"auto" | "ptt">("ptt"),
  holding = ref(false),
  feedback = ref(false),
  approved = ref(false),
  transcript = ref(false);
const ready = computed(() =>
  reviewThreads.flatMap((thread) =>
    thread.items
      .filter((item) => item.state === "ready")
      .map((item) => ({ thread, item })),
  ),
);
onMounted(async () => {
  await nextTick();
  const rail = root.value?.querySelector(".col-left");
  if (!rail) return;
  const host = document.createElement("div");
  rail.insertBefore(host, rail.lastElementChild);
  target.value = host;
});
onBeforeUnmount(() => target.value?.remove());
function open(selectedThread: ReviewThread, selectedItem: ReviewItem) {
  thread.value = selectedThread;
  item.value = selectedItem;
  feedback.value = false;
  approved.value = false;
  approvalDialog.value?.close();
  transcript.value = false;
  dialog.value?.showModal();
}
function close() {
  holding.value = false;
  approvalDialog.value?.close();
  dialog.value?.close();
}
function release() {
  if (holding.value) {
    holding.value = false;
    feedback.value = true;
  }
}
const preview = `<!doctype html><html lang="en"><meta name="viewport" content="width=device-width"><style>body{margin:0;background:#172322;color:#ecebe3;font:16px system-ui;padding:65px 8%;text-align:center}small{letter-spacing:3px;color:#9eb9ac}h1{font:54px Georgia;margin:25px 0}p{color:#b5c6ba}.crew{display:flex;justify-content:center;gap:28px;margin:75px 0}.person{width:130px;padding:35px 12px;border:1px solid #64776a;border-radius:60px 60px 15px 15px;background:#233732}.person b{display:block;font:40px Georgia;color:#c6d7aa;margin-bottom:18px}.person span{font-size:12px}footer{margin-top:70px;font:22px Georgia;color:#c6d7aa}

.approval-dialog { border: 0; padding: 0; border-radius: 12px; color: #e4e7ee; background: #242e3c; }
.approval-dialog::backdrop { background: #0008; }
</style><small>NOISY STUDIO · FICTIONAL REVIEW ARTIFACT</small><h1>A company of characters.</h1><p>Shared ambition. A whole crew of different minds.</p><div class="crew"><div class="person"><b>M</b>Mira<br><span>Design lead</span></div><div class="person"><b>R</b>Rook<br><span>Quality</span></div><div class="person"><b>L</b>Lux<br><span>Engineering</span></div></div><footer>“The team has opinions. That’s why it works.”</footer></html>`;
</script>
<template>
  <div ref="root" class="task-review-lab">
    <App /><Teleport v-if="target" :to="target"
      ><section class="task-panel">
        <header>
          <h2>Ready for review</h2>
          <span>{{ ready.length }}</span>
        </header>
        <div class="ready-list">
          <article v-for="result in ready" :key="result.item.id">
            <div>
              <strong :title="result.item.title">{{ result.item.title }}</strong
              ><small :title="result.thread.title">{{
                result.thread.title
              }}</small>
            </div>
            <button
              @click="open(result.thread, result.item)"
              :aria-label="'Review ' + result.item.title"
            >
              Review ↗
            </button>
          </article>
        </div>
        <header class="work-heading">
          <h2>Work by thread</h2>
          <small>demo</small>
        </header>
        <div class="thread-list" tabindex="0" aria-label="Thread tasks">
          <section
            v-for="parent in reviewThreads"
            :key="parent.id"
            class="thread"
          >
            <h3 tabindex="0" :title="parent.title">{{ parent.title }}</h3>
            <small>{{
              parent.items.length > 1
                ? "Manager · " + parent.items.length + " delegated work items"
                : "Solo · no subagents"
            }}</small>
            <div v-for="work in parent.items" :key="work.id" class="work-item">
              <div class="work-title">
                <span tabindex="0" :title="work.title">{{ work.title }}</span
                ><button
                  v-if="work.review"
                  @click="open(parent, work)"
                  :aria-label="'Review ' + work.title"
                >
                  ↗
                </button>
              </div>
              <div class="work-meta">
                <small
                  >{{ work.owner }} ·
                  <b :class="work.state">{{ work.state }}</b></small
                >
                <div
                  class="track"
                  :aria-label="
                    work.completed + ' of ' + work.total + ' steps complete'
                  "
                >
                  <i
                    :style="{
                      width: (work.completed / work.total) * 100 + '%',
                    }"
                  />
                </div>
              </div>
            </div>
          </section>
        </div></section
    ></Teleport>
    <dialog
      ref="dialog"
      class="review-dialog"
      :class="header"
      @cancel="holding = false"
    >
      <header class="review-header">
        <button
          class="back"
          aria-label="Back to dashboard"
          title="Back to dashboard"
          @click="close"
        >
          ←
        </button>
        <div class="recipient">
          <VoiceAvatar :voice="thread.voice" :size="32" set="editorial" />
          <div>
            <strong :title="thread.title">{{ thread.title }}</strong
            ><small
              >Feedback → main thread
              <span v-if="thread.items.length > 1"
                >· {{ item.owner }}’s work</span
              ></small
            >
          </div>
        </div>
        <div class="conversation" aria-live="polite">
          <small>{{
            feedback ? "YOU → MAIN THREAD · DEMO" : "MAIN THREAD · REVIEW READY"
          }}</small>
          <p>
            {{
              feedback
                ? "I like the direction. Please make the labels larger and keep the layout compact. The current names are hard to read at a distance."
                : "Ready for your feedback on " + item.title + "."
            }}
          </p>
          <button @click="transcript = !transcript" :aria-expanded="transcript">
            Transcript
          </button>
        </div>
        <div class="voice-controls">
          <label
            >Mode
            <select v-model="mode" @change="holding = false">
              <option value="ptt">Push to talk</option>
              <option value="auto">Auto</option>
            </select></label
          ><button
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
            {{ holding ? "Recording…" : "Hold for feedback" }}</button
          ><button
            v-else
            class="auto"
            @click="feedback = true"
            title="Simulate speech; microphone is off"
          >
            ● Listening to main thread
          </button>
        </div>
        <button
          v-if="!approved"
          class="approve"
          @click="approvalDialog?.showModal()"
        >
          Approve…</button
        ><button
          v-else
          class="approved"
          @click="approved = false"
          title="Undo simulated approval"
        >
          ✓ Approved · Undo</button
        ><a
          class="external"
          :href="item.review"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="'Open ' + item.title + ' externally'"
          title="Open externally"
          >↗</a
        ><span class="demo-label">DEMO · MIC OFF</span>
      </header>
      <aside v-if="transcript" class="transcript">
        <header>
          <strong>Review conversation · demo</strong
          ><button @click="transcript = false" aria-label="Close transcript">
            ✕
          </button>
        </header>
        <p><b>Main thread:</b> Ready for your feedback on {{ item.title }}.</p>
        <p v-if="feedback">
          <b>You:</b> I like the direction. Please make the labels larger and
          keep the layout compact. The current names are hard to read at a
          distance.
        </p>
        <small>No audio captured. Sample feedback is not sent.</small>
      </aside>
      <section class="artifact">
        <div v-if="unavailable" class="fallback">
          <h2>Open this result in a separate tab.</h2>
          <p>
            This site does not allow embedded previews. Keep this review
            workspace open for feedback and approval.
          </p>
          <a :href="item.review" target="_blank" rel="noopener noreferrer"
            >Open review ↗</a
          ><small>Embedding restriction demonstration · no policy bypass</small>
        </div>
        <iframe
          v-else
          title="Synthetic review artifact"
          sandbox=""
          :srcdoc="preview"
        />
      </section>
      <dialog
        ref="approvalDialog"
        class="approval-dialog"
        aria-labelledby="confirm-title"
      >
        <section
          class="confirmation"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <h2 id="confirm-title">Approve this result?</h2>
          <p>{{ item.title }}</p>
          <small
            >Approval returns to the main thread: {{ thread.title }}. Opening a
            result or giving feedback does not approve it.</small
          >
          <div>
            <button @click="approvalDialog?.close()">Keep reviewing</button
            ><button
              @click="
                approved = true;
                approvalDialog?.close();
              "
            >
              Yes, approve result
            </button>
          </div>
          <small>Prototype only · no approval is sent</small>
        </section>
      </dialog>
    </dialog>
  </div>
</template>
<style scoped>
.task-panel {
  padding: 8px 12px;
  border: 1px solid var(--line, #363a43);
  border-radius: 8px;
  color: var(--ink, #e4e7ee);
  background: var(--panel, #202329);
  font: 11px var(--sans, system-ui);
}
.task-panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0 9px;
}
.task-panel h2 {
  font-size: 11px;
  margin: 0;
}
.task-panel header span {
  color: var(--brand-accent, #a8c8ef);
}
.task-panel small {
  color: var(--muted, #9ba5b5);
  font-size: 9px;
}
.ready-list article {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 0;
  border-top: 1px solid #77839b22;
}
.ready-list article > div {
  min-width: 0;
  flex: 1;
}
.ready-list strong {
  display: block;
  font-size: 10px;
  font-weight: 500;
  line-height: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ready-list small {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 8px;
  margin-top: 3px;
}
.task-panel button {
  border: 0;
  background: none;
  color: var(--brand-accent, #a8c8ef);
  font: inherit;
  font-size: 9px;
  cursor: pointer;
  white-space: nowrap;
  padding: 3px;
}
.work-heading {
  border-top: 1px solid #77839b44;
  margin-top: 9px;
  padding-top: 13px !important;
}
.thread-list {
  max-height: 318px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.thread {
  margin: 0 0 13px;
}
.thread h3 {
  font-size: 10px;
  font-weight: 600;
  margin: 0 0 4px;
  line-height: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.thread > small {
  font-size: 8px;
}
.work-item {
  border-left: 1px solid #77839b44;
  padding: 5px 0 4px 8px;
  margin-left: 3px;
}
.work-title {
  display: flex;
  align-items: center;
  gap: 4px;
}
.work-title > span {
  font-size: 9px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  line-height: 16px;
}
.work-title button {
  font-size: 12px;
  padding: 0 2px;
}
.work-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.work-meta small {
  font-size: 8px;
  flex: 1;
}
.work-meta b {
  font-weight: 400;
}
.ready {
  color: var(--brand-accent, #a8c8ef);
}
.blocked {
  color: #d9ad73;
}
.track {
  width: 37px;
  height: 2px;
  background: #77839b44;
}
.track i {
  height: 100%;
  display: block;
  background: var(--brand-accent, #a8c8ef);
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
  font: 12px var(--sans, system-ui);
  --header-height: 88px;
}
.review-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px 15px;
  border-bottom: 1px solid #39404b;
  box-sizing: border-box;
  position: relative;
  background: #202731;
}
.review-dialog button,
.review-dialog select {
  font: inherit;
  color: inherit;
  background: #2b3441;
  border: 1px solid #506076;
  border-radius: 5px;
  padding: 7px 9px;
  cursor: pointer;
}
.recipient {
  display: flex;
  gap: 9px;
  align-items: center;
  width: 245px;
  flex-shrink: 0;
  min-width: 0;
}
.recipient > div {
  min-width: 0;
}
.recipient strong {
  font-size: 11px;
  font-weight: 500;
  line-height: 15px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.recipient small {
  display: block;
  font-size: 8px;
  color: #aab8cc;
  margin-top: 4px;
}
.recipient small span {
  display: none;
}
.conversation {
  flex: 1;
  min-width: 100px;
  padding: 7px 40px 7px 10px;
  background: #a5c4eb0b;
  border-left: 2px solid #a5c4eb;
  max-height: 60px;
  box-sizing: border-box;
  position: relative;
}
.conversation small {
  font-size: 7px;
  color: #aab8cc;
  display: block;
}
.conversation p {
  font-size: 10px;
  line-height: 14px;
  margin: 3px 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.conversation button {
  position: absolute;
  right: 4px;
  top: 7px;
  border: 0;
  background: none;
  font-size: 7px;
  padding: 0;
  writing-mode: vertical-rl;
}
.voice-controls {
  display: flex;
  gap: 6px;
  align-items: center;
}
.voice-controls label {
  font-size: 0;
}
.voice-controls select {
  font-size: 10px;
  padding: 7px 4px;
  width: 91px;
}
.voice-controls button {
  font-size: 10px;
  white-space: nowrap;
}
.talk {
  background: #b7cae8 !important;
  color: #14202e !important;
  touch-action: none;
}
.auto {
  color: #bad9bc !important;
  font-size: 9px !important;
}
.approve,
.approved {
  white-space: nowrap;
  font-size: 10px !important;
}
.external {
  color: #c6d9f6;
  font-size: 22px;
  text-decoration: none;
  padding: 6px;
}
.demo-label {
  position: absolute;
  bottom: 3px;
  right: 17px;
  color: #91a1b7;
  font-size: 7px;
  letter-spacing: 0.07em;
}
.artifact {
  height: calc(100% - var(--header-height));
}
iframe {
  width: 100%;
  height: 100%;
  border: 0;
  background: #172322;
}
.transcript {
  position: absolute;
  right: 22px;
  top: calc(var(--header-height) + 8px);
  width: min(440px, calc(100vw - 44px));
  max-height: 230px;
  overflow: auto;
  box-sizing: border-box;
  padding: 16px;
  background: #242e3c;
  border: 1px solid #738298;
  border-radius: 9px;
  z-index: 3;
  box-shadow: 0 8px 35px #0005;
}
.transcript header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.transcript p {
  font-size: 12px;
  line-height: 1.6;
}
.transcript small {
  color: #aab8cc;
  font-size: 10px;
}
.transcript button {
  padding: 3px 7px;
}
.confirmation-backdrop {
  position: absolute;
  inset: 0;
  background: #0008;
  display: grid;
  place-items: center;
  z-index: 5;
}
.confirmation {
  background: #242e3c;
  border: 1px solid #8497ad;
  padding: 25px;
  border-radius: 12px;
  width: min(410px, calc(100vw - 70px));
  box-shadow: 0 15px 50px #0008;
}
.confirmation h2 {
  font-size: 19px;
  margin-top: 0;
}
.confirmation p {
  font-size: 14px;
  line-height: 1.5;
}
.confirmation small {
  display: block;
  font-size: 11px;
  line-height: 1.6;
  color: #b8c7d9;
}
.confirmation > div {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin: 22px 0 14px;
}
.confirmation button {
  font-size: 11px;
}
.fallback {
  max-width: 470px;
  margin: auto;
  padding: 100px 25px;
  text-align: center;
}
.fallback p {
  line-height: 1.6;
  color: #acb8c8;
}
.fallback a {
  color: #b7cae8;
}
.fallback small {
  display: block;
  margin-top: 25px;
  color: #acb8c8;
  font-size: 10px;
}
.ribbon {
  --header-height: 98px;
}
.ribbon .review-header {
  display: grid;
  grid-template-columns: 35px minmax(210px, 1fr) auto auto 30px;
  grid-template-rows: 36px 31px;
  gap: 5px 12px;
  padding: 8px 16px 13px;
}
.ribbon .recipient {
  width: auto;
}
.ribbon .recipient strong {
  -webkit-line-clamp: 1;
}
.ribbon .recipient small span {
  display: inline;
}
.ribbon .conversation {
  grid-column: 2/5;
  grid-row: 2;
  max-height: 31px;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 4px 60px 4px 10px;
}
.ribbon .conversation small {
  white-space: nowrap;
}
.ribbon .conversation p {
  -webkit-line-clamp: 1;
  margin: 0;
}
.ribbon .conversation button {
  writing-mode: initial;
  top: 8px;
  right: 6px;
}
.ribbon .external {
  grid-column: 5;
  grid-row: 1;
}
.companion.review-dialog {
  --header-height: 84px;
  padding: 0;
  border: 0;
  max-height: none;
  display: revert;
}
.companion.review-dialog .recipient {
  width: 190px;
}
.companion.review-dialog .conversation {
  background: #314051;
  border-radius: 12px;
  border-left: 0;
  padding-left: 14px;
}
.companion.review-dialog .voice-controls {
  flex-direction: column;
  gap: 3px;
}
.companion.review-dialog .voice-controls select {
  padding: 3px 4px;
}
.companion.review-dialog .talk {
  padding: 5px 8px;
}
.review-dialog button:focus-visible,
a:focus-visible,
.task-panel button:focus-visible,
.task-panel [tabindex]:focus-visible {
  outline: 2px solid #b7d4ff;
  outline-offset: 2px;
}
@media (max-width: 1000px) {
  .review-dialog {
    --header-height: 120px;
  }
  .review-header {
    flex-wrap: wrap;
    gap: 6px;
  }
  .recipient {
    width: calc(100% - 60px);
  }
  .conversation {
    order: 5;
    flex: 1;
  }
  .voice-controls {
    order: 6;
  }
  .approve,
  .approved {
    order: 7;
  }
  .external {
    position: absolute;
    right: 12px;
    top: 12px;
  }
  .ribbon .review-header {
    grid-template-columns: 30px minmax(100px, 1fr) auto 30px;
    grid-template-rows: 38px 50px;
  }
  .ribbon .recipient {
    width: auto;
  }
  .ribbon .voice-controls {
    grid-column: 3;
    grid-row: 1;
  }
  .ribbon .approve,
  .ribbon .approved {
    grid-column: 3;
    grid-row: 2;
  }
  .ribbon .conversation {
    grid-column: 2;
    grid-row: 2;
    height: 42px;
    max-height: 42px;
    display: block;
  }
  .ribbon .external {
    position: static;
    grid-column: 4;
  }
  .ribbon {
    --header-height: 120px;
  }
  .companion.review-dialog {
    --header-height: 120px;
  }
  .companion.review-dialog .recipient {
    width: calc(100% - 60px);
  }
}
.approval-dialog {
  border: 0;
  padding: 0;
  border-radius: 12px;
  color: #e4e7ee;
  background: #242e3c;
}
.approval-dialog::backdrop {
  background: #0008;
}
</style>
