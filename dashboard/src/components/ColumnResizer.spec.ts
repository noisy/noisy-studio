import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ColumnResizer from "./ColumnResizer.vue";

describe("ColumnResizer", () => {
  it("resizes by keyboard steps and resets on double-click", async () => {
    const wrapper = mount(ColumnResizer, { props: { width: 300 } });
    const handle = wrapper.get("[role=separator]");

    await handle.trigger("keydown", { key: "ArrowRight" });
    await handle.trigger("keydown", { key: "ArrowLeft" });
    await handle.trigger("keydown", { key: "Enter" });
    await handle.trigger("dblclick");

    expect([wrapper.emitted("resize"), wrapper.emitted("reset")?.length]).toEqual([[[316], [284]], 1]);
  });
});
