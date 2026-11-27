import { computed, type Ref } from "vue";
import type { DaemonStatus } from "../types";

/** What each agent is doing, read from the daemon's activity map.
 *
 * The hooks set an agent's activity at every tool step and clear it when
 * the turn ends, but its timestamp only moves at tool boundaries. So:
 * - thinking: activity updated in the last few seconds - the live violet
 *   pulse in the status slot.
 * - busy: activity present at all - a long tool call is still work. The
 *   age cap only guards against a lost end-of-turn hook; its text is the
 *   row's tooltip. */
const THINKING_FRESH_S = 20;
const BUSY_STALE_S = 600;

export function useAgentActivity(status: Ref<DaemonStatus | null>) {
  const withActivity = (maxAgeS: number) => computed(() => {
    const activity = status.value?.activity ?? {};
    const now = Date.now() / 1000;
    return Object.entries(activity)
      .filter(([, a]) => a?.text && now - a.at < maxAgeS)
      .map(([name]) => name);
  });
  const thinking = withActivity(THINKING_FRESH_S);
  const busy = withActivity(BUSY_STALE_S);
  const activityText = computed(() =>
    Object.fromEntries(busy.value.map((name) => [name, status.value?.activity?.[name]?.text ?? ""])),
  );
  return { thinking, activityText };
}
