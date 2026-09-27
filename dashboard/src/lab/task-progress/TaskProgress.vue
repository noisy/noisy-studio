<script setup lang="ts">
import { computed, ref } from "vue";
import TaskDetail from "./TaskDetail.vue";
import { conversations, counts, scenarios } from "./fixtures";
import type { Work } from "./fixtures";
const props = withDefaults(
  defineProps<{
    variant?:
      | "compact"
      | "ledger"
      | "cards"
      | "checklist"
      | "owners"
      | "combined";
    theme?: "dark" | "light";
    scenario?:
      | "normal"
      | "idle"
      | "stale"
      | "blocked"
      | "completed"
      | "unknown";
    narrow?: boolean;
  }>(),
  { variant: "ledger", theme: "dark", scenario: "normal", narrow: false },
);
const selected = ref("astra");
const opened = ref(new Set<string>());
const rows = computed(() =>
  conversations.map((w, i) =>
    i === 0 && props.scenario !== "normal"
      ? props.scenario === "unknown"
        ? {
            ...w,
            state: "unknown" as const,
            tasks: null,
            updated: "No update available",
          }
        : scenarios[props.scenario]
      : w,
  ),
);
const current = computed(
  () => rows.value.find((w) => w.id === selected.value) ?? rows.value[0]!,
);
const detailOnly = computed(
  () => props.variant === "checklist" || props.variant === "owners",
);
const ready = computed(
  () =>
    rows.value.filter((w) => w.state === "done" && w.review && !visited(w))
      .length,
);
function visited(w: Work) {
  return w.visited || opened.value.has(w.id);
}
function summary(w: Work) {
  if (w.tasks === null) return "No task info";
  if (!w.tasks.length) return "No active tasks";
  const n = counts(w);
  return `${n.done} done · ${n.working} active · ${n.pending} pending${n.blocked ? " · " + n.blocked + " blocked" : ""}`;
}
function active(w: Work) {
  return (
    w.tasks?.find((t) => t.state === "blocked" || t.state === "working")
      ?.title ??
    (w.state === "done"
      ? "All reported tasks complete"
      : "Waiting for a task update")
  );
}
</script>
<template>
  <main
    class="task-lab"
    :class="[theme, { narrow, 'compact-layout': variant === 'compact' }]"
  >
    <div class="lab-heading">
      <span>NOISY STUDIO / DESIGN LAB</span>
      <h1>Know what needs you.</h1>
      <p>Task progress · {{ variant }} · fictional data</p>
    </div>
    <div class="workspace">
      <aside class="rail">
        <div class="context-panel">
          <span>SESSION USAGE</span
          ><small>Codex · 38% remaining · resets in 2h</small>
        </div>
        <section class="progress-panel">
          <header class="panel-heading">
            <h2>{{ detailOnly ? "This conversation" : "Crew progress" }}</h2>
            <span v-if="!detailOnly" class="ready-count"
              >{{ ready }} to review</span
            >
          </header>
          <TaskDetail
            v-if="detailOnly"
            :work="current"
            :variant="variant === 'owners' ? 'owners' : 'checklist'"
          />
          <div
            v-else
            class="rows"
            :class="variant"
            tabindex="0"
            aria-label="Conversation progress list"
          >
            <article
              v-for="work in rows"
              :key="work.id"
              class="work-row"
              :class="{
                selected: current.id === work.id,
                ready: work.state === 'done' && work.review && !visited(work),
              }"
            >
              <button
                class="select-row"
                @click="selected = work.id"
                :aria-expanded="
                  variant === 'combined' ? current.id === work.id : undefined
                "
                :aria-pressed="current.id === work.id"
              >
                <div class="row-top">
                  <strong>{{ work.name }}</strong
                  ><span class="state" :class="work.state">{{
                    work.state === "unknown"
                      ? "No task info"
                      : work.state === "stale"
                        ? "Update overdue"
                        : work.state === "done" && work.review && !visited(work)
                          ? "Ready for review"
                          : work.state === "done"
                            ? "Done"
                            : work.state
                  }}</span>
                </div>
                <span class="topic">{{ work.topic }}</span>
                <div class="meter-slot">
                  <div
                    v-if="work.tasks?.length"
                    class="meter"
                    :aria-label="`${counts(work).done} of ${counts(work).total} tasks complete`"
                  >
                    <i
                      :style="{
                        width: `${(counts(work).done / counts(work).total) * 100}%`,
                      }"
                    />
                  </div>
                  <span v-else class="unknown-line">{{
                    work.tasks === null
                      ? "Task reporting unavailable"
                      : "No work in progress"
                  }}</span>
                </div>
                <span class="counts">{{ summary(work) }}</span
                ><span class="current-task"
                  ><span
                    v-if="variant === 'compact' && work.tasks?.length"
                    class="compact-count"
                    >{{ counts(work).done }}/{{ counts(work).total }} done · </span
                  >{{ active(work) }}</span
                ><span class="age"
                  >{{ work.state === "stale" ? "Last report " : ""
                  }}{{ work.updated
                  }}{{
                    work.state === "stale" ? " · may still be working" : ""
                  }}</span
                >
              </button>
              <div class="review-slot">
                <a
                  v-if="work.review"
                  :href="work.review.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  @click="opened.add(work.id)"
                  >{{
                    visited(work) ? "Open again ↗" : work.review.label + " ↗"
                  }}</a
                ><span v-if="work.review && visited(work)" class="visited"
                  >Opened · approval not recorded</span
                ><span
                  v-else-if="work.state === 'done' && !work.review"
                  class="subtle"
                  >Done · no review target supplied</span
                >
              </div>
              <TaskDetail
                v-if="variant === 'combined' && current.id === work.id"
                :work="work"
                variant="owners"
              />
            </article>
          </div>
          <footer class="panel-foot">
            {{
              variant === "combined"
                ? "Select a conversation to expand its tasks."
                : "Conversation order matches your tabs."
            }}
          </footer>
        </section>
        <div class="context-panel">
          <span>TURN HISTORY</span><small>Latest turn · 2m ago</small>
        </div>
      </aside>
      <section v-if="!narrow" class="conversation-preview">
        <span class="eyebrow">VIEWED CONVERSATION</span>
        <h2>{{ current.name }}</h2>
        <p>{{ current.topic }}</p>
        <div class="note">
          <span class="spark">✦</span>
          <div>
            <strong>Progress without interrupting.</strong>
            <p>
              See who is working, what is blocked, and which result is ready to
              open.
            </p>
          </div>
        </div>
        <TaskDetail
          v-if="!detailOnly && variant !== 'combined'"
          :work="current"
          variant="owners"
        />
        <div class="design-note">
          <strong>Design choices</strong>
          <p v-if="variant === 'compact'">
            A compact glance: six conversations fit in the rail. Select a row to
            read the full task list beside it. Review links remain directly
            accessible.
          </p>
          <p v-else-if="variant === 'ledger'">
            A familiar ledger: rows in tab order, with review actions always in
            the same place.
          </p>
          <p v-else-if="variant === 'cards'">
            Cards separate each conversation more clearly, using the same fixed
            information slots.
          </p>
          <p v-else-if="variant === 'combined'">
            One panel for overview and detail. Expansion stays inside a
            fixed-height scroll region.
          </p>
          <p v-else>
            Detailed tasks
            {{
              variant === "owners"
                ? "grouped by owner, making delegation visible"
                : "in work order, making the plan easy to follow"
            }}.
          </p>
          <small
            >Prototype only. Opening a result does not mark it approved. Task
            reporting and live updates are a separate implementation.</small
          >
        </div>
      </section>
    </div>
  </main>
</template>
<style scoped>
.task-lab {
  --tp-bg: #17191d;
  --tp-surface: #202329;
  --tp-text: #e8e9ed;
  --tp-muted: #a0a6b2;
  --tp-line: #353a43;
  --tp-accent: #a8c8ef;
  --tp-tint: #a8c8ef10;
  --tp-warning: #efbe7e;
  --tp-warning-bg: #efbe7e10;
  background: var(--tp-bg);
  color: var(--tp-text);
  font-family: var(--sans, system-ui, sans-serif);
  min-height: 100vh;
  padding: 30px;
  box-sizing: border-box;
}
.light {
  --tp-bg: #f1f2f4;
  --tp-surface: #fff;
  --tp-text: #272c35;
  --tp-muted: #606a79;
  --tp-line: #d6dbe2;
  --tp-accent: #365f90;
  --tp-tint: #365f900b;
  --tp-warning: #865212;
  --tp-warning-bg: #8652120b;
}
.lab-heading {
  max-width: 1120px;
  margin: 0 auto 25px;
}
.lab-heading > span,
.eyebrow {
  font-size: 10px;
  letter-spacing: 0.15em;
  color: var(--tp-muted);
}
h1 {
  font-size: 27px;
  letter-spacing: -0.7px;
  margin: 10px 0;
}
.lab-heading p {
  font-size: 12px;
  color: var(--tp-muted);
  margin: 0;
}
.workspace {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 28px;
  max-width: 1120px;
  margin: auto;
}
.rail {
  min-width: 0;
}
.context-panel {
  height: 48px;
  box-sizing: border-box;
  border: 1px solid var(--tp-line);
  border-radius: 9px;
  margin-bottom: 12px;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--tp-muted);
  gap: 10px;
}
.context-panel span {
  font-size: 9px;
  letter-spacing: 0.08em;
}
.context-panel small {
  font-size: 9px;
}
.progress-panel {
  border: 1px solid var(--tp-line);
  border-radius: 10px;
  background: var(--tp-surface);
  overflow: hidden;
  margin-bottom: 12px;
}
.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 16px;
  border-bottom: 1px solid var(--tp-line);
}
h2 {
  font-size: 14px;
  margin: 0;
  font-weight: 600;
}
.ready-count {
  font-size: 10px;
  border-radius: 5px;
  background: var(--tp-tint);
  color: var(--tp-accent);
  border: 1px solid var(--tp-accent);
  padding: 4px 7px;
}
.rows {
  height: 610px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.work-row {
  border-bottom: 1px solid var(--tp-line);
  padding: 13px 14px 9px;
  position: relative;
  min-height: 166px;
  box-sizing: border-box;
}
.work-row.selected {
  background: var(--tp-tint);
}
.work-row.ready {
  box-shadow: inset 3px 0 var(--tp-accent);
}
.select-row {
  display: block;
  width: 100%;
  border: 0;
  background: none;
  padding: 0;
  text-align: left;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.row-top strong {
  font-size: 13px;
}
.state {
  font-size: 9px;
  color: var(--tp-muted);
  text-transform: capitalize;
}
.state.done {
  color: var(--tp-accent);
}
.state.blocked,
.state.stale {
  color: var(--tp-warning);
}
.topic {
  display: block;
  font-size: 11px;
  color: var(--tp-muted);
  margin-top: 4px;
}
.meter-slot {
  height: 18px;
  display: flex;
  align-items: center;
}
.meter {
  height: 3px;
  width: 100%;
  background: var(--tp-line);
  border-radius: 5px;
  overflow: hidden;
}
.meter i {
  display: block;
  height: 100%;
  background: var(--tp-accent);
}
.unknown-line {
  font-size: 10px;
  color: var(--tp-muted);
}
.counts {
  display: block;
  font-size: 10px;
  color: var(--tp-muted);
  line-height: 17px;
}
.current-task {
  display: block;
  font-size: 11px;
  line-height: 20px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.age {
  display: block;
  font-size: 9px;
  color: var(--tp-muted);
  line-height: 16px;
}
.review-slot {
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
}
.review-slot a {
  color: var(--tp-accent);
  font-size: 11px;
  text-decoration: none;
  font-weight: 600;
}
.review-slot a:hover {
  text-decoration: underline;
}
.visited {
  font-size: 8px;
  color: var(--tp-muted);
  max-width: 115px;
  text-align: right;
}
.subtle {
  font-size: 9px;
  color: var(--tp-muted);
}
.panel-foot {
  padding: 12px 14px;
  color: var(--tp-muted);
  border-top: 1px solid var(--tp-line);
  font-size: 10px;
}
.cards {
  padding: 10px;
  box-sizing: border-box;
}
.cards .work-row {
  border: 1px solid var(--tp-line);
  border-radius: 8px;
  margin-bottom: 9px;
  padding: 12px;
}
.combined .detail {
  margin-top: 8px;
}
.conversation-preview {
  padding: 18px 10px;
}
.conversation-preview > h2 {
  font-size: 30px;
  margin: 12px 0 5px;
}
.conversation-preview > p {
  font-size: 13px;
  color: var(--tp-muted);
}
.note {
  display: flex;
  gap: 14px;
  border-bottom: 1px solid var(--tp-line);
  padding: 25px 0;
  margin-bottom: 24px;
}
.spark {
  color: var(--tp-accent);
  font-size: 24px;
}
.note strong {
  font-size: 13px;
}
.note p {
  font-size: 12px;
  color: var(--tp-muted);
  line-height: 1.7;
  margin: 5px 0;
}
.design-note {
  margin-top: 26px;
  border-left: 2px solid var(--tp-line);
  padding-left: 16px;
  max-width: 480px;
}
.design-note strong {
  font-size: 12px;
}
.design-note p,
.design-note small {
  font-size: 11px;
  color: var(--tp-muted);
  line-height: 1.7;
}
.narrow {
  max-width: 390px;
  padding: 16px;
  margin: auto;
}
.narrow .workspace {
  display: block;
}
.narrow h1 {
  font-size: 24px;
}
button:focus-visible,
a:focus-visible,
.rows:focus-visible {
  outline: 2px solid var(--tp-accent);
  outline-offset: 3px;
}
@media (max-width: 700px) {
  .task-lab {
    padding: 15px;
  }
  .workspace {
    grid-template-columns: minmax(0, 1fr);
  }
  .conversation-preview {
    display: none;
  }
  .rail {
    max-width: 400px;
    width: 100%;
    margin: auto;
  }
}

.rows.compact {
  height: 432px;
}
.compact .work-row {
  height: 72px;
  min-height: 72px;
  padding: 7px 12px;
}
.compact .topic,
.compact .meter-slot,
.compact .counts,
.compact .age {
  display: none;
}
.compact .current-task {
  font-size: 10px;
  line-height: 16px;
}
.compact-count {
  color: var(--tp-muted);
}
.compact .row-top {
  line-height: 16px;
}
.compact .review-slot {
  height: 20px;
}
.compact .review-slot a {
  font-size: 10px;
}
.compact .visited {
  font-size: 8px;
  max-width: 130px;
}

.compact-layout {
  padding: 20px;
}
.compact-layout .workspace {
  grid-template-columns: 268px minmax(0, 1fr);
}
.compact-layout .lab-heading {
  margin-bottom: 16px;
}
.compact-layout h1 {
  font-size: 23px;
  margin: 6px 0;
}
.compact-layout .context-panel {
  height: 38px;
  padding: 8px 12px;
}
.compact-layout .context-panel small {
  max-width: 120px;
  text-align: right;
  font-size: 8px;
}
.compact-layout .panel-heading {
  padding: 12px;
}
.compact-layout .visited {
  max-width: 82px;
  font-size: 7px;
}
.compact-layout.narrow .workspace {
  display: block;
}
@media (max-width: 700px) {
  .compact-layout .workspace {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
