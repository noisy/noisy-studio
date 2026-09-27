import { mount } from "@vue/test-utils";
import { afterEach, expect, it, vi } from "vitest";
import ProviderLimits from "./ProviderLimits.vue";
const snapshot = {
  provider: "claude",
  label: "Claude",
  scope: "connection" as const,
  message: "",
  sampled_at: 1000,
  windows: [
    { label: "Session", used_percent: 92, resets_at: 1060, stale: false },
  ],
};
afterEach(() => vi.useRealTimers());
it("expires a reset without turning last known usage into available quota", () => {
  vi.useFakeTimers();
  vi.setSystemTime(1000_000);
  const wrapper = mount(ProviderLimits, { props: { providers: [snapshot] } });
  expect(wrapper.text()).toContain("in 1m");
  vi.advanceTimersByTime(61_000);
  return wrapper.vm.$nextTick().then(() => {
    expect(wrapper.find(".window").classes()).toContain("stale");
    expect(wrapper.text()).toContain("92%");
    wrapper.unmount();
  });
});
it("shows only supplied registered providers and no invented unknown bar", () => {
  const wrapper = mount(ProviderLimits, {
    props: {
      providers: [
        {
          ...snapshot,
          provider: "grok",
          label: "Grok",
          windows: [],
          message: "Usage unavailable",
        },
      ],
    },
  });
  expect({
    text: wrapper.text(),
    meters: wrapper.findAll("[role=meter]").length,
  }).toEqual({
    text: "Plan limits % used · resetsGrokUsage unavailable",
    meters: 0,
  });
  wrapper.unmount();
});
