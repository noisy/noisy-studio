import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CatchUpBar from "./CatchUpBar.vue";

describe("CatchUpBar", () => {
  it("offers summarize first, then one-by-one catch up and skip", async () => {
    const wrapper = mount(CatchUpBar, { props: { count: 5, canSummarize: true } });

    for (const button of wrapper.findAll("button")) await button.trigger("click");

    expect({
      labels: wrapper.findAll("button").map((button) => button.text()),
      emitted: Object.keys(wrapper.emitted()).filter((name) => name !== "click"),
    }).toEqual({
      labels: ["Σ Summarize 5 unheard", "▶ Catch up one by one", "Skip all"],
      emitted: ["summarize", "catchUp", "skip"],
    });
  });

  it("disables summarize while the session is offline", () => {
    const wrapper = mount(CatchUpBar, { props: { count: 5, canSummarize: false } });

    expect(wrapper.find(".summarize").attributes("disabled")).toBeDefined();
  });

  it("renders nothing when every message was heard", () => {
    const wrapper = mount(CatchUpBar, { props: { count: 0, canSummarize: true } });

    expect(wrapper.find(".catchup-row").exists()).toBe(false);
  });
});
