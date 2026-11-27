import { effectScope, nextTick, ref } from "vue";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useSustainedWork } from "./useSustainedWork";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

it("reports an agent only after it has worked without a break for the hold time", async () => {
  const scope = effectScope();
  const thinking = ref<string[]>(["a"]);
  const sustained = scope.run(() => useSustainedWork(thinking, 10_000))!;
  vi.advanceTimersByTime(9_000);
  expect(sustained.value).toEqual([]);
  vi.advanceTimersByTime(1_000);
  expect(sustained.value).toEqual(["a"]);

  // A break resets the clock: a short tool call later does not count.
  thinking.value = [];
  await nextTick();
  expect(sustained.value).toEqual([]);
  thinking.value = ["a"];
  await nextTick();
  vi.advanceTimersByTime(5_000);
  expect(sustained.value).toEqual([]);
  scope.stop();
});
