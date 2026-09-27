<script setup lang="ts">
import {
  computed,
  watch,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from "vue";
import App from "../../App.vue";
import QuotaHistory from "./QuotaHistory.vue";
withDefaults(
  defineProps<{ variant?: "rows" | "secondary" | "legend" | "columns" }>(),
  {
    variant: "rows",
  },
);
const root = ref<HTMLElement | null>(null);
const summaryTarget = ref<HTMLElement | null>(null);
const detailsTarget = ref<HTMLElement | null>(null);
const details = ref(false);
const section = ref("History");
const windowName = ref("Session");
const previewNow = Date.now();
const providers = [
  {
    name: "Claude",
    windows: [
      { label: "Session", used: 76, seconds: 42 * 60, color: "warning" },
      { label: "Weekly", used: 48, seconds: 80 * 3600, color: "brand-accent" },
    ],
  },
  {
    name: "Codex",
    windows: [
      { label: "Session", used: 36, seconds: 2 * 3600, color: "brand-accent" },
      { label: "Weekly", used: 61, seconds: 53 * 3600, color: "brand-accent" },
    ],
  },
  {
    name: "Grok",
    windows: [{ label: "Weekly", used: 92, seconds: 5 * 86400, color: "red" }],
  },
];
function countdown(seconds: number) {
  if (seconds <= 0) return "Awaiting update";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${Math.floor(seconds / 86400)}d${hours ? ` ${hours}h` : ""}`;
}
function resetTooltip(provider: string, label: string, seconds: number) {
  if (seconds <= 0)
    return "Reset passed; waiting for a fresh sample. No current estimate.";
  const time = new Date(previewNow + seconds * 1000).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  return `${provider} ${label}: resets ${time} local time. Account-wide; synthetic snapshot.`;
}
const selectedProvider = ref("Claude");
watch(selectedProvider, () => {
  windowName.value = selectedProvider.value === "Grok" ? "Weekly" : "Session";
});
const selectedWindows = computed(
  () =>
    providers.find((provider) => provider.name === selectedProvider.value)
      ?.windows ?? [],
);
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
        aria-label="Provider limits, shared across conversations"
      >
        <header>
          <h2>Plan limits <small>% used · demo</small></h2>
          <button @click="details = true">Details ↗</button>
        </header>
        <p v-if="variant === 'legend'" class="reset-legend">
          ↻ time until reset
        </p>
        <div
          v-for="provider in providers"
          :key="provider.name"
          class="provider-block"
        >
          <h3>{{ provider.name }}</h3>
          <div class="quota-windows">
            <div
              v-for="window in provider.windows"
              :key="window.label"
              class="quota-row"
              :style="{ '--quota-color': `var(--${window.color})` }"
            >
              <span>{{ window.label }}</span>
              <div
                class="quota-track"
                role="meter"
                :aria-label="`${provider.name} ${window.label} percent used`"
                :aria-valuenow="window.used"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <i :style="{ width: `${window.used}%` }" />
              </div>
              <strong>{{ window.used }}%</strong>
              <span
                class="reset-time"
                tabindex="0"
                :title="
                  resetTooltip(provider.name, window.label, window.seconds)
                "
                :aria-label="
                  resetTooltip(provider.name, window.label, window.seconds)
                "
                >{{ variant === "legend" ? "↻ " : "resets in "
                }}{{ countdown(window.seconds) }}</span
              >
            </div>
          </div>
        </div>
      </section>
    </Teleport>
    <Teleport v-if="detailsTarget" :to="detailsTarget">
      <section v-if="details" class="usage-details" aria-label="Usage details">
        <header>
          <div>
            <h1>Usage</h1>
            <p>Provider limits · account-wide, shared across conversations</p>
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
              >Provider
              <select v-model="selectedProvider">
                <option>Claude</option>
                <option>Codex</option>
                <option>Grok</option>
              </select></label
            >
            <label
              >Window
              <select v-model="windowName">
                <option v-for="window in selectedWindows" :key="window.label">
                  {{ window.label }}
                </option>
              </select></label
            ><span>Illustrative data · sampled every 5m</span>
          </div>
          <template
            v-for="window in selectedWindows.filter(
              (item) => item.label === windowName,
            )"
            :key="window.label"
          >
            <div class="history-numbers">
              <div>
                <small>Last reported</small
                ><strong>{{ window.used }}% <em>used</em></strong>
              </div>
              <div>
                <small>Resets in</small
                ><strong>{{ countdown(window.seconds) }}</strong>
              </div>
              <div>
                <small>Sample age</small><strong>15m <em>stale</em></strong>
              </div>
            </div>
            <QuotaHistory
              :last-used="window.used"
              :weekly="window.label !== 'Session'"
            />
          </template>
          <p v-if="selectedProvider === 'Grok'" class="explanation">
            Grok plan allowance is a shared weekly pool. These values are
            fictional; a supported collector is not verified. Grok API limits
            are separate per-model RPS and TPM limits.
          </p>
          <p v-else class="explanation">
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

.provider-block {
  margin-top: 8px;
}
.provider-block h3 {
  font: 600 10px var(--sans);
  margin-bottom: 4px;
}
.provider-block h3 small {
  font: 9px var(--sans);
  color: var(--muted);
  margin-left: 6px;
}
.quota-row {
  grid-template-columns: 44px minmax(0, 1fr) 27px 75px;
  gap: 5px;
}
.reset-time {
  font: 9px var(--sans);
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
}
.reset-time:focus-visible {
  outline: 1px solid var(--brand-accent);
}
.reset-legend {
  font: 9px var(--sans);
  color: var(--muted);
  margin: 0 0 5px;
}
.legend .quota-row {
  grid-template-columns: 44px minmax(0, 1fr) 27px 50px;
}
.secondary .quota-row {
  grid-template-columns: 44px minmax(0, 1fr) 27px;
  height: auto;
  gap: 3px 6px;
}
.secondary .reset-time {
  grid-column: 2/4;
  text-align: left;
  font-size: 9px;
}
.secondary .quota-windows {
  gap: 5px;
}
.columns .quota-row {
  grid-template-columns: 1fr auto;
}
.columns .reset-time {
  grid-row: 3;
  grid-column: 1/-1;
  text-align: left;
  font-size: 8px;
}
.columns .quota-windows {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}
.history-heading {
  flex-wrap: wrap;
}
</style>
