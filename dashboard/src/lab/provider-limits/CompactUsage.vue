<script setup lang="ts">
import { computed, ref, watch } from "vue";
import QuotaHistory from "./QuotaHistory.vue";
const props = withDefaults(
  defineProps<{
    variant?: "meters" | "rows" | "badges";
    light?: boolean;
    startInDetails?: boolean;
  }>(),
  { variant: "meters" },
);
const details = ref(props.startInDetails ?? false);
const section = ref("OVERVIEW");
const account = ref("Claude Code");
const period = ref("5-hour");
watch(account, () => {
  period.value = account.value === "Codex" ? "Weekly" : "5-hour";
});
const current = computed(() =>
  account.value === "Codex"
    ? { used: 36, reset: "5d 2h" }
    : period.value === "Weekly · Opus"
      ? { used: 92, reset: "1d 4h" }
      : period.value === "Weekly"
        ? { used: 48, reset: "3d 8h" }
        : { used: 76, reset: "42m" },
);
const amber = ref(70);
const red = ref(90);
const providers = [
  {
    name: "Claude",
    used: 92,
    reset: "1d 4h",
    window: "Opus weekly",
    color: "red",
  },
  {
    name: "Codex",
    used: 36,
    reset: "5d 2h",
    window: "Weekly",
    color: "brand-accent",
  },
];
</script>
<template>
  <main class="compact-lab" :class="{ light }">
    <header class="appbar">
      <strong>NOISY STUDIO <small>DESIGN LAB</small></strong
      ><span>Microphone ready <i>●</i></span
      ><button disabled>Mute all agents</button
      ><button disabled>Settings</button>
    </header>
    <div class="dashboard-grid">
      <aside class="left-rail">
        <div class="mic-actions">
          <button disabled>Mute mic<small>Click to pause</small></button
          ><button disabled>Hold to talk<small>or hold Space</small></button>
        </div>
        <section class="rail-panel">
          <h2>01 <b>Microphone</b></h2>
          <svg class="wave" viewBox="0 0 240 34" aria-hidden="true">
            <path
              d="M0 18H38L43 13L48 23L52 6L57 29L62 12L67 21L72 17H101L108 8L114 27L120 3L125 29L133 12L139 22L145 17H240"
            />
          </svg>
          <p class="level">LEVEL <span>━━━━━━━━━━━━</span> −42 dB</p>
        </section>
        <section class="rail-panel">
          <h2>02 <b>Audio spectrum</b></h2>
          <div class="spectrum">
            <i
              v-for="n in 30"
              :key="n"
              :style="{ height: `${8 + ((n * 13) % 27)}px` }"
            />
          </div>
        </section>
        <section class="rail-panel">
          <h2>03 <b>Audio controls</b><span class="more">More ↗</span></h2>
          <div class="control">
            <span>Language</span><strong>English⌄</strong>
          </div>
          <div class="control">
            <span>Turn detection</span
            ><strong>Auto · <b>Push to talk</b></strong>
          </div>
          <div class="control">
            <span>End silence</span><strong>1.5s⌄</strong>
          </div>
        </section>
        <section class="rail-panel quota-mini" :class="variant">
          <h2>
            04 <b>Plan limits</b
            ><button @click="details = true">Details ↗</button>
          </h2>
          <div class="mini-items">
            <div
              v-for="provider in providers"
              :key="provider.name"
              class="mini-item"
              :style="{ '--quota-tone': `var(--${provider.color})` }"
            >
              <div class="mini-line">
                <span>{{ provider.name }}</span
                ><strong>{{ provider.used }}% used</strong
                ><small v-if="variant === 'rows'">↻ {{ provider.reset }}</small>
              </div>
              <div v-if="variant === 'meters'" class="mini-bar">
                <i :style="{ width: `${provider.used}%` }" />
              </div>
            </div>
          </div>
          <p>Account-wide · highest current window</p>
        </section>
        <section class="rail-panel">
          <h2>05 <b>Speech costs</b></h2>
          <div class="cost">
            <strong>$0.42</strong
            ><small>Recognition $0.09<br />Speech $0.33</small>
          </div>
        </section>
        <p class="rail-note">268px dashboard rail · synthetic data</p>
      </aside>
      <section v-if="!details" class="conversation-panel">
        <div class="conversation-tabs">
          <strong>Atlas</strong><span>Nova</span><span>Scout</span>
        </div>
        <header>
          <h1>Release preparation</h1>
          <p>Claude Code · Atlas</p>
        </header>
        <article class="bubble">
          <small>ATLAS · PLAYED</small>
          <p>
            The release checklist is ready. I’m checking the remaining tasks
            with the crew.
          </p>
        </article>
        <article class="bubble user">
          <small>YOU · DELIVERED</small>
          <p>Let’s keep going.</p>
        </article>
        <div class="empty-space">
          Your conversation stays the focus.<br />Account limits take only a few
          lines on the left.
        </div>
        <footer>
          <span>Language EN</span><span>Queue 0</span
          ><span>Service ONLINE</span>
        </footer>
      </section>
      <section v-else class="usage-view">
        <header class="usage-header">
          <div>
            <small>ACCOUNT OVERVIEW</small>
            <h1>Usage</h1>
            <p>Agent plan limits, shared across conversations.</p>
          </div>
          <button @click="details = false">← Back to conversation</button>
        </header>
        <nav aria-label="Usage sections">
          <button
            v-for="item in ['OVERVIEW', 'HISTORY', 'ATTRIBUTION', 'ALERTS']"
            :key="item"
            :aria-pressed="section === item"
            @click="section = item"
          >
            {{ item }}
          </button>
        </nav>
        <template v-if="section === 'OVERVIEW' || section === 'HISTORY'"
          ><div class="filters">
            <label
              >Account
              <select v-model="account">
                <option>Claude Code</option>
                <option>Codex</option>
              </select></label
            ><label
              >Window
              <select v-model="period">
                <option v-if="account === 'Claude Code'">5-hour</option>
                <option>Weekly</option>
                <option v-if="account === 'Claude Code'">Weekly · Opus</option>
              </select></label
            ><span>Illustrative history</span>
          </div>
          <div class="summary-grid">
            <div>
              <small>LAST REPORTED</small
              ><strong>{{ current.used }}% <em>used</em></strong>
            </div>
            <div>
              <small>RESET IN</small><strong>{{ current.reset }}</strong>
            </div>
            <div>
              <small>SAMPLE AGE</small
              ><strong class="muted">15m <em>stale</em></strong>
            </div>
          </div>
          <section class="graph-panel">
            <header>
              <h2>
                {{ account }} · {{ account === "Codex" ? "Weekly" : period }}
              </h2>
              <span>Used quota · %</span>
            </header>
            <QuotaHistory
              :last-used="current.used"
              :weekly="account === 'Codex' || period !== '5-hour'"
            />
          </section>
          <p class="notice">
            Last sample 15 minutes ago · collection stopped. The line ends at
            the last observation; it does not assume continued usage.
          </p>
          <p v-if="section === 'OVERVIEW'" class="explanation">
            Usage is reported for the provider account. Two agents using the
            same account share these limits.
          </p></template
        >
        <template v-else-if="section === 'ATTRIBUTION'"
          ><h2 class="section-title">
            Which conversations used the allowance?
          </h2>
          <p class="explanation">
            Account quota changes cannot reliably tell us. Other sessions may be
            active, and provider percentages may be rounded or delayed.
          </p>
          <div
            class="attribution-row"
            v-for="name in [
              'Atlas · Release preparation',
              'Nova · Dashboard polish',
              'Other sessions on this account',
            ]"
            :key="name"
          >
            <span>{{ name }}</span
            ><strong>Attribution unavailable</strong>
          </div>
          <p class="notice">
            No percentages are assigned to conversations. A future activity
            timeline could show sessions alongside account usage, clearly
            labelled as correlation.
          </p></template
        >
        <template v-else
          ><h2 class="section-title">Usage thresholds</h2>
          <p class="explanation">
            Design controls only. No notification or account setting is changed.
          </p>
          <div class="alert-controls">
            <label
              >Amber at
              <input v-model.number="amber" type="number" min="1" max="99" /> %
              used</label
            ><label
              >Red at
              <input v-model.number="red" type="number" min="2" max="100" /> %
              used</label
            >
          </div>
          <p v-if="amber >= red" class="notice">Amber must be below red.</p>
          <p class="explanation">
            Defaults: amber 70% · red 90%. Historical samples remain visible
            when stale, without claiming current availability.
          </p></template
        >
      </section>
    </div>
    <p class="lab-caption">
      {{
        variant === "meters"
          ? "A · Tiny meters"
          : variant === "rows"
            ? "B · Text + reset"
            : "C · Single-line badges"
      }}
      — click Details to open a separate Usage view, outside Settings. Synthetic
      fixture only.
    </p>
  </main>
</template>
<style scoped>
.compact-lab {
  min-height: 100vh;
  background: var(--bg0);
  color: var(--ink);
  padding: 16px 20px;
  font: 13px var(--sans);
  overflow: auto;
}
.light {
  --bg0: #f4f5f7;
  --bg1: #fff;
  --panel: #fff;
  --line: #d8dce3;
  --ink: #272a31;
  --muted: #616976;
  --brand-accent: #287e77;
  --warning: #986300;
  --red: #b94040;
  --surface-hover: #eef0f4;
  color-scheme: light;
}
button,
select,
input {
  background: var(--bg1);
  border: 1px solid var(--line);
  color: var(--ink);
  border-radius: 6px;
  padding: 6px 9px;
  font: 11px var(--sans);
}
button {
  cursor: pointer;
}
button:disabled {
  cursor: default;
}
.appbar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 17px;
}
.appbar > strong {
  font-size: 14px;
  letter-spacing: 0.08em;
}
.appbar small {
  font-size: 9px;
  color: var(--muted);
  margin-left: 8px;
}
.appbar > span {
  margin-left: auto;
  font-size: 11px;
  color: var(--muted);
}
.appbar i {
  color: var(--brand-accent);
  font-style: normal;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 268px minmax(0, 1fr);
  gap: 20px;
  max-width: 1600px;
  min-height: 700px;
}
.left-rail {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.mic-actions {
  display: flex;
  gap: 6px;
  margin-bottom: 5px;
}
.mic-actions button {
  flex: 1;
  padding: 12px 4px;
  color: var(--brand-accent);
  opacity: 1;
}
.mic-actions small {
  display: block;
  font-size: 9px;
  color: var(--muted);
  margin-top: 5px;
}
.rail-panel {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 12px;
  background: var(--panel);
}
.rail-panel h2 {
  display: flex;
  align-items: center;
  gap: 7px;
  font: 9px var(--mono);
  color: var(--muted);
  margin-bottom: 8px;
}
.rail-panel h2 b {
  font: 11px var(--sans);
  color: var(--ink);
  font-weight: 600;
}
.more {
  margin-left: auto;
  color: var(--brand-accent);
}
.wave {
  width: 100%;
  height: 32px;
  fill: none;
  stroke: var(--brand-accent);
}
.level {
  font: 9px var(--mono);
  color: var(--muted);
  display: flex;
  justify-content: space-between;
}
.level span {
  color: var(--brand-accent);
}
.spectrum {
  display: flex;
  gap: 4px;
  align-items: end;
  height: 38px;
}
.spectrum i {
  flex: 1;
  background: var(--agent-accent);
  opacity: 0.55;
  border-radius: 2px;
}
.control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  line-height: 25px;
  color: var(--muted);
}
.control strong {
  font-weight: 400;
  color: var(--ink);
}
.control b {
  font-weight: 500;
  color: var(--brand-accent);
}
.quota-mini h2 button {
  margin-left: auto;
  padding: 0;
  border: 0;
  background: none;
  color: var(--brand-accent);
  font-size: 10px;
}
.mini-items {
  display: grid;
  gap: 8px;
}
.mini-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
}
.mini-line strong {
  margin-left: auto;
  font-weight: 500;
  color: var(--quota-tone);
}
.mini-line small {
  font-size: 9px;
  color: var(--muted);
}
.mini-bar {
  height: 3px;
  margin-top: 4px;
  background: var(--line);
  border-radius: 3px;
}
.mini-bar i {
  display: block;
  height: 100%;
  background: var(--quota-tone);
  border-radius: inherit;
}
.quota-mini p {
  font-size: 9px;
  color: var(--muted);
  margin-top: 7px;
}
.badges .mini-items {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.badges .mini-line {
  gap: 5px;
  font-size: 9px;
}
.cost {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cost > strong {
  font-size: 20px;
  font-weight: 500;
}
.cost small {
  font-size: 9px;
  color: var(--muted);
  line-height: 1.6;
}
.rail-note,
.lab-caption {
  font-size: 10px;
  color: var(--muted);
  margin-top: 10px;
}
.conversation-panel,
.usage-view {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  min-width: 0;
  overflow: hidden;
}
.conversation-tabs {
  display: flex;
  gap: 25px;
  padding: 15px 24px;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.conversation-tabs strong {
  color: var(--brand-accent);
}
.conversation-tabs span {
  color: var(--muted);
}
.conversation-panel > header {
  padding: 22px 24px;
}
.conversation-panel h1 {
  font-size: 20px;
  font-weight: 500;
}
.conversation-panel header p {
  font-size: 11px;
  color: var(--muted);
  margin-top: 7px;
}
.bubble {
  border-left: 2px solid var(--agent-accent);
  background: var(--bg1);
  margin: 10px 24px;
  padding: 16px;
  border-radius: 8px;
  max-width: 680px;
}
.bubble small {
  font: 9px var(--mono);
  color: var(--agent-accent);
}
.bubble p {
  margin-top: 9px;
  font-size: 13px;
  line-height: 1.65;
}
.bubble.user {
  border-color: var(--brand-accent);
  margin-left: 70px;
}
.bubble.user small {
  color: var(--brand-accent);
}
.empty-space {
  padding: 70px 24px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
  text-align: center;
}
.conversation-panel footer {
  display: flex;
  gap: 22px;
  border-top: 1px solid var(--line);
  padding: 13px 24px;
  font: 9px var(--mono);
  color: var(--muted);
}
.usage-view {
  padding: 24px;
}
.usage-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: start;
}
.usage-header small {
  font: 9px var(--mono);
  color: var(--brand-accent);
}
.usage-header h1 {
  font-size: 27px;
  font-weight: 500;
  margin: 6px 0;
}
.usage-header p,
.explanation {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}
.usage-view nav {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--line);
  padding: 21px 0 14px;
}
.usage-view nav button {
  font: 10px var(--mono);
  background: transparent;
  border-color: transparent;
}
.usage-view nav button[aria-pressed="true"] {
  background: var(--surface-hover);
  color: var(--brand-accent);
  border-color: var(--line);
}
.filters {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 22px 0;
}
.filters label {
  font-size: 11px;
  color: var(--muted);
}
.filters select {
  margin-left: 5px;
}
.filters > span {
  margin-left: auto;
  color: var(--muted);
  font-size: 10px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 25px 0;
  gap: 15px;
}
.summary-grid small {
  font: 9px var(--mono);
  color: var(--muted);
  display: block;
  margin-bottom: 10px;
}
.summary-grid strong {
  font-size: 25px;
  font-weight: 500;
}
.summary-grid em {
  font-style: normal;
  font-size: 12px;
  color: var(--muted);
}
.summary-grid .muted {
  color: var(--muted);
}
.graph-panel {
  border: 1px solid var(--line);
  background: var(--bg1);
  border-radius: 10px;
  padding: 20px;
}
.graph-panel header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}
.graph-panel h2 {
  font-size: 13px;
  font-weight: 500;
}
.graph-panel header span {
  font-size: 10px;
  color: var(--muted);
}
.notice {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.6;
  padding: 12px;
  border-left: 2px solid var(--warning);
  background: var(--bg1);
  margin: 17px 0;
}
.section-title {
  font-size: 18px;
  font-weight: 500;
  margin: 25px 0 12px;
}
.attribution-row {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  border-bottom: 1px solid var(--line);
  padding: 20px 0;
  font-size: 12px;
}
.attribution-row strong {
  font-weight: 400;
  color: var(--muted);
}
.alert-controls {
  display: flex;
  gap: 25px;
  padding: 25px 0;
  font-size: 12px;
}
.alert-controls input {
  width: 60px;
  margin: 0 8px;
}
@media (max-width: 850px) {
  .compact-lab {
    padding: 12px;
  }
  .appbar small,
  .appbar > span {
    display: none;
  }
  .appbar {
    flex-wrap: wrap;
  }
  .dashboard-grid {
    grid-template-columns: 268px minmax(0, 1fr);
    gap: 12px;
  }
  .usage-header {
    flex-direction: column;
  }
  .usage-view {
    padding: 16px;
  }
  .filters {
    flex-wrap: wrap;
  }
  .filters > span {
    margin-left: 0;
  }
  .summary-grid strong {
    font-size: 19px;
  }
}
@media (max-width: 650px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .left-rail {
    max-width: 268px;
  }
  .appbar > strong {
    width: 100%;
  }
  .summary-grid {
    gap: 8px;
  }
  .attribution-row {
    flex-direction: column;
  }
  .usage-view {
    overflow: auto;
  }
  .graph-panel {
    padding: 10px;
  }
  .alert-controls {
    flex-wrap: wrap;
  }
}
</style>
