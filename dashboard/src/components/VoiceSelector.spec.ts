import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import VoiceSelector from "./VoiceSelector.vue";

describe("VoiceSelector", () => {
  it("returns keyboard focus to the trigger when Escape closes the options", async () => {
    const wrapper = mount(VoiceSelector, { props: { voice: "rex" }, attachTo: document.body });
    await wrapper.get(".voicecur").trigger("click");
    await wrapper.get(".voicelist .row").trigger("keydown", { key: "Escape" });
    expect(document.activeElement).toBe(wrapper.get(".voicecur").element);
    expect(wrapper.find(".voicelist").exists()).toBe(false);
    wrapper.unmount();
  });
  it("shows the current voice uppercase, without a gender label", () => {
    const wrapper = mount(VoiceSelector, { props: { voice: "altair" } });

    expect(wrapper.find(".vname").text()).toBe("ALTAIR");
    expect(wrapper.find(".vg").exists()).toBe(false); // gender dropped — the face says it
    expect(wrapper.find(".voicelist").exists()).toBe(false); // collapsed
  });

  it("picking a voice from the grid emits it and closes the grid", async () => {
    const wrapper = mount(VoiceSelector, { props: { voice: "altair" } });

    await wrapper.find(".voicecur").trigger("click");
    const rex = wrapper.findAll(".voicelist .row").find((b) => b.find(".name").text() === "REX")!;
    await rex.trigger("click");

    expect(wrapper.emitted("change")).toEqual([["rex"]]);
    expect(wrapper.find(".voicelist").exists()).toBe(false); // list closes
  });

  it("re-picking the current voice closes without emitting", async () => {
    const wrapper = mount(VoiceSelector, { props: { voice: "rex" } });

    await wrapper.find(".voicecur").trigger("click");
    const rex = wrapper.findAll(".voicelist .row").find((b) => b.find(".name").text() === "REX")!;
    await rex.trigger("click");

    expect(wrapper.emitted("change")).toBeUndefined();
  });
});

it('uses the active provider voice label without changing portrait identity', () => {
  const wrapper = mount(VoiceSelector, {props:{voice:'lux',voiceLabels:{lux:'Sarah · US'}}});
  expect(wrapper.find('.vname').text()).toBe('SARAH · US');
  wrapper.unmount();
});
