import { getCurrentScope, onScopeDispose, ref, watch, type Ref } from "vue";

/** Agents that have been working CONTINUOUSLY for at least `holdMs`.
 *
 * The conversation list moves working sessions into their own section; a
 * raw "is working" flag would make a row jump down for every short tool
 * call and back up a second later. Only sustained work moves it. */
export const SUSTAINED_WORK_MS = 10_000;
const TICK_MS = 1_000;

export function useSustainedWork(
  thinking: Ref<string[]>,
  holdMs = SUSTAINED_WORK_MS,
  now: () => number = Date.now,
): Ref<string[]> {
  const since = new Map<string, number>();
  const sustained = ref<string[]>([]);
  function update() {
    const t = now();
    const current = new Set(thinking.value);
    for (const name of [...since.keys()]) if (!current.has(name)) since.delete(name);
    for (const name of current) if (!since.has(name)) since.set(name, t);
    const next = [...since].filter(([, start]) => t - start >= holdMs).map(([name]) => name).sort();
    if (next.join("\0") !== sustained.value.join("\0")) sustained.value = next;
  }
  watch(thinking, update, { immediate: true });
  const timer = setInterval(update, TICK_MS);
  if (getCurrentScope()) onScopeDispose(() => clearInterval(timer));
  return sustained;
}
