import { onMounted, onBeforeUnmount, ref, inject, provide, type InjectionKey } from "vue";
import { getTaskProgress } from "../api/client";
import type { TaskSnapshot } from "../components/task-progress/types";
const taskProgressKey: InjectionKey<ReturnType<typeof createTaskProgress>> = Symbol("task-progress");
export function provideTaskProgress() {
  const progress = createTaskProgress();
  provide(taskProgressKey, progress);
  return progress;
}
export function useTaskProgress() {
  return inject(taskProgressKey, null) ?? createTaskProgress();
}
function createTaskProgress() {
  const snapshot = ref<TaskSnapshot>({ threads: {}, error: null }),
    error = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined,
    controller: AbortController | undefined,
    disposed = false,
    generation = 0;
  async function refresh() {
    if (disposed) return;
    clearTimeout(timer);
    controller?.abort();
    const request = ++generation;
    const requestController = new AbortController();
    controller = requestController;
    const timeout = setTimeout(() => requestController.abort(), 5000);
    try {
      const value = await getTaskProgress(requestController.signal);
      if (!disposed && request === generation) {
        snapshot.value = value;
        error.value = value.error ?? "";
      }
    } catch (reason) {
      if (!disposed && request === generation)
        error.value =
          reason instanceof Error
            ? reason.message
            : "Task progress unavailable";
    } finally {
      clearTimeout(timeout);
      if (!disposed && request === generation)
        timer = setTimeout(refresh, 5000);
    }
  }
  onMounted(refresh);
  onBeforeUnmount(() => {
    disposed = true;
    generation++;
    clearTimeout(timer);
    controller?.abort();
  });
  return { snapshot, error, refresh };
}
