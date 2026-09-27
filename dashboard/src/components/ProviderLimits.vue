<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import type { ProviderQuota } from "../types";
const props = defineProps<{ providers: ProviderQuota[]; offline?: boolean }>();
const now = ref(Date.now() / 1000);
const timer = setInterval(() => {
  now.value = Date.now() / 1000;
}, 1000);
onBeforeUnmount(() => clearInterval(timer));
const providers = computed(() =>
  props.providers.map((provider) => ({
    ...provider,
    windows: provider.windows.map((window) => ({
      ...window,
      stale:
        props.offline ||
        window.stale ||
        !provider.sampled_at ||
        now.value - provider.sampled_at > 300 ||
        (!!window.resets_at && now.value >= window.resets_at),
    })),
  })),
);
function reset(window: ProviderQuota["windows"][number]) {
  if (
    props.offline ||
    window.stale ||
    (window.resets_at && window.resets_at <= now.value)
  )
    return "stale";
  if (!window.resets_at) return "reset unknown";
  const minutes = Math.max(1, Math.ceil((window.resets_at - now.value) / 60));
  if (minutes < 60) return `in ${minutes}m`;
  if (minutes < 1440) return `in ${Math.floor(minutes / 60)}h`;
  return `in ${Math.floor(minutes / 1440)}d`;
}
function tooltip(window: ProviderQuota["windows"][number]) {
  return window.stale
    ? "Last known usage; waiting for a fresh sample."
    : window.resets_at
      ? `Resets ${new Date(window.resets_at * 1000).toLocaleString()}. Shared across conversations on this connection.`
      : "Reset time unavailable.";
}
</script>
<template>
  <section
    v-if="providers.length"
    class="provider-limits"
    aria-label="Agent plan limits"
  >
    <h2>Plan limits <small>% used · resets</small></h2>
    <div
      v-for="(provider, index) in providers"
      :key="`${provider.provider}-${index}`"
      class="provider"
    >
      <h3>
        {{ provider.label
        }}<small
          v-if="
            providers.filter((item) => item.provider === provider.provider)
              .length > 1
          "
        >
          · connection {{ index + 1 }}</small
        >
      </h3>
      <p v-if="!provider.windows.length">
        {{ offline ? "Disconnected" : provider.message }}
      </p>
      <div
        v-for="(window, windowIndex) in provider.windows"
        :key="windowIndex"
        class="window"
        :class="{ stale: window.stale }"
        :style="{
          '--quota-tone': window.stale
            ? 'var(--muted)'
            : window.used_percent >= 90
              ? 'var(--red)'
              : window.used_percent >= 70
                ? 'var(--warning)'
                : 'var(--brand-accent)',
        }"
      >
        <span class="window-label" :title="window.label">{{
          window.label
        }}</span>
        <div
          class="track"
          role="meter"
          :aria-label="`${provider.label} ${window.label} ${window.stale ? 'last known ' : ''}percent used`"
          :aria-valuenow="window.used_percent"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <i :style="{ width: `${window.used_percent}%` }" />
        </div>
        <strong>{{ Math.round(window.used_percent) }}%</strong
        ><span
          class="reset"
          tabindex="0"
          :title="tooltip(window)"
          :aria-label="tooltip(window)"
          >{{ reset(window) }}</span
        >
      </div>
    </div>
  </section>
</template>
<style scoped>
.provider-limits {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 8px 12px;
  margin-bottom: 6px;
  background: var(--panel);
  min-width: 0;
}
h2 {
  font: 600 12px var(--sans);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
h2 small,
h3 small {
  font: 9px var(--sans);
  color: var(--muted);
}
.provider {
  margin-top: 8px;
}
h3 {
  font: 600 10px var(--sans);
  margin-bottom: 4px;
}
p {
  font: 10px var(--sans);
  color: var(--muted);
}
.window {
  display: grid;
  grid-template-columns: 44px minmax(15px, 1fr) 29px 61px;
  gap: 5px;
  align-items: center;
  height: 17px;
  font: 10px var(--sans);
}
.window-label {
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.track {
  height: 4px;
  border-radius: 4px;
  background: var(--line);
  overflow: hidden;
}
.track i {
  height: 100%;
  display: block;
  background: var(--quota-tone);
}
strong {
  font: 10px var(--mono);
  color: var(--quota-tone);
  text-align: right;
}
.reset {
  font-size: 9px;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
}
.stale .track i {
  background: repeating-linear-gradient(
    110deg,
    var(--muted),
    var(--muted) 3px,
    var(--line) 3px,
    var(--line) 6px
  );
}
</style>
