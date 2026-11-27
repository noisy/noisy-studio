import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SnoozeMenu from "./SnoozeMenu.vue";

const wednesdayAfternoon = new Date(2026, 10, 25, 14, 30);
const epoch = (date: Date) => Math.floor(date.getTime() / 1000);

describe("SnoozeMenu", () => {
  it("lists each choice with the time it comes back, and picks its wake time", async () => {
    const wrapper = mount(SnoozeMenu, { props: { now: epoch(wednesdayAfternoon) } });
    const items = wrapper.findAll("button.snooze-item");

    expect(items.map((item) => [item.get("span").text(), item.get("time").text()])).toEqual([
      ["1 hour", "15:30"], ["3 hours", "17:30"], ["6 hours", "20:30"], ["Tomorrow", "Thu 09:00"], ["Next week", "Mon 09:00"],
    ]);
    await items[3].trigger("click");
    expect(wrapper.emitted("pick")).toEqual([[epoch(new Date(2026, 10, 26, 9))]]);
  });
});
