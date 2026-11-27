import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CatchUpBar from "./CatchUpBar.vue";

describe("CatchUpBar", () => {
  it("offers catch up, summarize and skip for the backlog", async () => {
    const wrapper = mount(CatchUpBar, { props: { count: 5, canSummarize: true } });

    for (const button of wrapper.findAll("button")) await button.trigger("click");

    expect({
      labels: wrapper.findAll("button").map((button) => button.text()),
      emitted: Object.keys(wrapper.emitted()).filter((name) => name !== "click"),
    }).toEqual({
      labels: ["▶ Catch up (5 unheard)", "Σ Summarize", "Skip all"],
      emitted: ["catchUp", "summarize", "skip"],
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
