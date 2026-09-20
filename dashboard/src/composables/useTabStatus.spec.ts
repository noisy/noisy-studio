import { effectScope, ref } from "vue";
import { afterEach, expect, it, vi } from "vitest";
import type { DaemonStatus } from "../types";
import { useTabStatus } from "./useTabStatus";

afterEach(() => vi.restoreAllMocks());

it.each([false, true])("never puts an active or speaking session path in the browser title (speaking=%s)", (speaking) => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const key = "/private/example/session-1";
  const status = ref({
    active_agent: key,
    agents_meta: { [key]: { label: key } },
    speaking_agents: speaking ? [key] : [],
  } as unknown as DaemonStatus);
  const scope = effectScope();

  scope.run(() => useTabStatus(status));

  expect(document.title).toBe(speaking
    ? "▶ New conversation — Noisy Studio"
    : "New conversation — Noisy Studio");
  scope.stop();
});
