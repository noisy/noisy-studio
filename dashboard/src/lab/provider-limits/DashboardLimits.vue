<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import App from "../../App.vue";
import QuotaHistory from "./QuotaHistory.vue";
withDefaults(defineProps<{ variant?: "rows" | "inset" | "columns" }>(), {
  variant: "rows",
});
const root = ref<HTMLElement | null>(null);
const summaryTarget = ref<HTMLElement | null>(null);
const detailsTarget = ref<HTMLElement | null>(null);
const details = ref(false);
const section = ref("History");
const windowName = ref("Session");
const windows = [
  { name: "Session", used: 76, reset: "42m", color: "warning" },
  { name: "Weekly", used: 48, reset: "3d 8h", color: "brand-accent" },
  { name: "Opus", used: 92, reset: "1d 4h", color: "red" },
];
onMounted(async () => {
  await nextTick();
  // Lab-only insertion into the real dashboard; no production slot or wiring.
  const rail = root.value?.querySelector(".col-left");
  const center = root.value?.querySelector(".col-mid");
  if (!rail || !center) return;
  const summary = document.createElement("div");
  const detail = document.createElement("div");
  summary.className = "quota-lab-summary-host";
  detail.className = "quota-lab-detail-host";
  rail.insertBefore(summary, rail.lastElementChild);
  center.prepend(detail);
  summaryTarget.value = summary;
  detailsTarget.value = detail;
});
onBeforeUnmount(() => {
  summaryTarget.value?.remove();
  detailsTarget.value?.remove();
});
</script>
<template>
  <div
    ref="root"
    class="dashboard-limits-lab"
    :class="{ 'usage-open': details }"
  >
    <App />
    <Teleport v-if="summaryTarget" :to="summaryTarget">
      <section
        class="quota-summary"
        :class="variant"
        aria-label="Claude plan usage, shared across conversations"
      >
        <header>
          <h2>Claude limits <small>% used</small></h2>
          <button @click="details = true">Details ↗</button>
        </header>
        <div class="quota-windows">
          <div
            v-for="window in windows"
            :key="window.name"
            class="quota-row"
            :style="{ '--quota-color': `var(--${window.color})` }"
            :title="`${window.name === 'Opus' ? 'Opus weekly' : window.name} · resets in ${window.reset} · account-wide`"
          >
            <span>{{ window.name === "Opus" ? "Opus wk" : window.name }}</span>
            <div
              class="quota-track"
              role="meter"
              :aria-label="`${window.name} percent used`"
              :aria-valuenow="window.used"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <i :style="{ width: `${window.used}%` }" />
            </div>
            <strong>{{ window.used }}%</strong>
          </div>
        </div>
      </section>
    </Teleport>
    <Teleport v-if="detailsTarget" :to="detailsTarget">
      <section v-if="details" class="usage-details" aria-label="Usage details">
        <header>
          <div>
            <h1>Usage</h1>
            <p>
              Claude plan limits · account-wide, shared across conversations
            </p>
          </div>
          <button @click="details = false">← Back</button>
        </header>
        <nav aria-label="Usage sections">
          <button
            v-for="item in ['History', 'Attribution']"
            :key="item"
            :aria-pressed="section === item"
            @click="section = item"
          >
            {{ item }}
          </button>
        </nav>
        <template v-if="section === 'History'">
          <div class="history-heading">
            <label
              >Window
              <select v-model="windowName">
                <option v-for="window in windows" :key="window.name">
                  {{ window.name }}
                </option>
              </select></label
            ><span>Illustrative data · sampled every 5m</span>
          </div>
          <template
            v-for="window in windows.filter((item) => item.name === windowName)"
            :key="window.name"
          >
            <div class="history-numbers">
              <div>
                <small>Last reported</small
                ><strong>{{ window.used }}% <em>used</em></strong>
              </div>
              <div>
                <small>Resets in</small><strong>{{ window.reset }}</strong>
              </div>
              <div>
                <small>Sample age</small><strong>15m <em>stale</em></strong>
              </div>
            </div>
            <QuotaHistory
              :last-used="window.used"
              :weekly="window.name !== 'Session'"
            />
          </template>
          <p class="explanation">
            The plot stops at the last sample. Gaps and reset boundaries are not
            joined. Historical values do not claim current availability.
          </p>
        </template>
        <template v-else
          ><h2 class="attribution-title">Usage by conversation</h2>
          <p class="explanation">
            Account quota changes cannot reliably identify which agent or
            conversation used the allowance.
          </p>
          <div
            v-for="name in ['Atlas', 'Nova', 'Other sessions']"
            :key="name"
            class="attribution-row"
          >
            <span>{{ name }}</span
            ><span>Attribution unavailable</span>
          </div>
          <p class="explanation">
            No estimated percentages are assigned. Activity alongside a quota
            chart would show correlation, not proven consumption.
          </p></template
        >
      </section>
    </Teleport>
  </div>
</template>
<style scoped>
.dashboard-limits-lab {
  height: 100vh;
}
.quota-summary {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 7px 12px;
  margin-bottom: 6px;
  min-width: 0;
}
.quota-summary header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  margin-bottom: 5px;
  height: 17px;
}
.quota-summary h2 {
  font: 600 12px var(--sans);
  white-space: nowrap;
}
.quota-summary h2 small {
  font: 9px var(--sans);
  color: var(--muted);
  margin-left: 4px;
}
.quota-summary button {
  border: 0;
  background: none;
  color: var(--brand-accent);
  font: 10px var(--sans);
  padding: 0;
}
.quota-windows {
  display: grid;
  gap: 4px;
}
.quota-row {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) 29px;
  align-items: center;
  gap: 7px;
  height: 13px;
  font: 10px var(--sans);
}
.quota-row > span {
  color: var(--muted);
}
.quota-row strong {
  color: var(--quota-color);
  font: 10px var(--mono);
  text-align: right;
}
.quota-track {
  height: 4px;
  background: var(--line);
  border-radius: 4px;
  overflow: hidden;
}
.quota-track i {
  display: block;
  height: 100%;
  background: var(--quota-color);
  border-radius: inherit;
}
.inset .quota-track {
  height: 9px;
  border-radius: 2px;
}
.inset .quota-track i {
  border-radius: 2px;
}
.inset .quota-row {
  grid-template-columns: 46px minmax(0, 1fr) 29px;
}
.columns .quota-windows {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.columns .quota-row {
  display: grid;
  grid-template-columns: 1fr auto;
  height: auto;
  gap: 6px 4px;
}
.columns .quota-track {
  grid-column: 1/-1;
  grid-row: 2;
}
.columns .quota-row strong {
  grid-column: 2;
  grid-row: 1;
}
.columns {
  padding-bottom: 10px;
}
.columns header {
  margin-bottom: 10px;
}
.dashboard-limits-lab :deep(.col-mid) {
  position: relative;
}
.usage-open :deep(.col-mid > :not(.quota-lab-detail-host)) {
  display: none;
}
.usage-open :deep(.quota-lab-detail-host) {
  height: 100%;
  overflow: auto;
}
.usage-details {
  height: 100%;
  min-height: 560px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 24px;
  color: var(--ink);
  overflow: auto;
}
.usage-details > header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 18px;
}
.usage-details h1 {
  font-size: 24px;
  font-weight: 500;
}
.usage-details header p {
  font-size: 11px;
  color: var(--muted);
  margin-top: 6px;
}
.usage-details button,
.usage-details select {
  background: var(--bg1);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 6px;
  font: 11px var(--sans);
  padding: 7px 11px;
}
.usage-details nav {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--line);
  padding: 20px 0 14px;
}
.usage-details nav button[aria-pressed="true"] {
  color: var(--brand-accent);
  background: var(--surface-hover);
}
.history-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin: 24px 0;
  color: var(--muted);
  font-size: 11px;
}
.history-heading select {
  margin-left: 8px;
}
.history-heading > span {
  font-size: 10px;
}
.history-numbers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-bottom: 24px;
  gap: 15px;
}
.history-numbers small {
  display: block;
  color: var(--muted);
  font-size: 10px;
  margin-bottom: 7px;
}
.history-numbers strong {
  font-size: 23px;
  font-weight: 500;
}
.history-numbers em {
  font-style: normal;
  font-size: 11px;
  color: var(--muted);
}
.explanation {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
  margin: 22px 0;
}
.attribution-title {
  font-size: 18px;
  margin-top: 24px;
}
.attribution-row {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.attribution-row span:last-child {
  color: var(--muted);
}
@media (max-width: 760px) {
  .usage-details {
    padding: 16px;
  }
  .history-heading {
    flex-wrap: wrap;
  }
  .history-numbers strong {
    font-size: 18px;
  }
}
</style>
