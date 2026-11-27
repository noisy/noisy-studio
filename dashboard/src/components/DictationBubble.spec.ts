import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import DictationBubble from "./DictationBubble.vue";

describe("DictationBubble", () => {
  it("says what happens to the words, in a slot that never changes size", () => {
    const phases = ["listening", "inserting", "inserted", "failed"] as const;
    const labels = phases.map((phase) => mount(DictationBubble, { props: { text: "x", phase } }).find(".label").text());
    expect(labels).toEqual(["Listening", "Pasting…", "Pasted", "Not pasted"]);
  });

  it("hangs below the cursor or stands above it", () => {
    const above = mount(DictationBubble, { props: { text: "x", phase: "listening", placement: "above" } });
    expect(above.find(".dictation-frame").classes()).toContain("above");
  });

  it("shows a hint until the first words arrive", () => {
    const w = mount(DictationBubble, { props: { text: "", phase: "listening" } });
    expect(w.find(".hint").exists()).toBe(true);
  });

  it("stays pinned to the newest words as they arrive", async () => {
    const w = mount(DictationBubble, { props: { text: "one", phase: "listening" }, attachTo: document.body });
    const body = w.find(".words").element as HTMLElement;
    Object.defineProperty(body, "scrollHeight", { configurable: true, value: 640 });
    await w.setProps({ text: "one two three" });
    await nextTick();
    expect(body.scrollTop).toBe(640);
    w.unmount();
  });
});
