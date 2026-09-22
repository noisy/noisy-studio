import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SettingsView from "./SettingsView.vue";

describe("SettingsView", () => {
  it("shows the key as a masked form field plus the pricing/link guidance", async () => {
    const wrapper = mount(SettingsView, { props: { apiKeyHint: "····kRc9" } });
    await wrapper.findAll(".tabbtn").find((b) => b.text() === "System")!.trigger("click");

    const stored = wrapper.find(".keyinput.stored");
    expect((stored.element as HTMLInputElement).value).toContain("kRc9");
    expect((stored.element as HTMLInputElement).value).toContain("••••");
    expect(wrapper.text()).toContain("$0.10 per hour of audio");
    const links = wrapper.findAll("a").map((a) => a.attributes("href"));
    expect(links).toContain("https://console.x.ai");
    expect(links).toContain("https://x.ai/api");
  });

  it("emits save with the entered key and hides the input again", async () => {
    const wrapper = mount(SettingsView, { props: { apiKeyHint: "····kRc9" } });
    await wrapper.findAll(".tabbtn").find((b) => b.text() === "System")!.trigger("click");

    await wrapper.find(".btn").trigger("click"); // REPLACE
    await wrapper.find("input.keyinput").setValue("xai-new-key-123");
    await wrapper.find("input.keyinput").trigger("keyup.enter");

    expect(wrapper.emitted("save")).toEqual([["xai-new-key-123"]]);
    // Back to the readonly masked field — the editable input is gone.
    expect(wrapper.find(".keyinput.stored").exists()).toBe(true);
    expect(wrapper.findAll("input.keyinput")).toHaveLength(1);
  });

  it("rejects obviously-not-a-key input without emitting", async () => {
    const wrapper = mount(SettingsView, { props: { apiKeyHint: "" } });
    await wrapper.findAll(".tabbtn").find((b) => b.text() === "System")!.trigger("click");

    await wrapper.find(".btn").trigger("click");
    await wrapper.find("input.keyinput").setValue("abc");
    await wrapper.find("input.keyinput").trigger("keyup.enter");

    expect(wrapper.emitted("save")).toBeUndefined();
  });

  it("offers native microphones without browser audio choices", async () => {
    const closed = mount(SettingsView, { props: { apiKeyHint: "····kRc9" } });
    await closed.findAll(".tabbtn").find((b) => b.text() === "Audio")!.trigger("click");
    expect(closed.find('option[value="browser"]').exists()).toBe(false);

  });

  it("moves the keys to a Hotkeys tab and keeps a pointer in Audio (#104)", async () => {
    const w = mount(SettingsView, {
      props: { apiKeyHint: "····kRc9", hotkeys: { configured: true, permission: "missing", armed: false, stored: { hold: "F8" }, problems: {} } },
    });
    await w.findAll(".tabbtn").find((b) => b.text() === "Audio")!.trigger("click");
    expect(w.find("select[aria-label='Hold-to-talk key']").exists()).toBe(false);
    await w.find(".linkbtn").trigger("click");
    expect(w.find(".hotkeys").exists()).toBe(true);
    expect(w.find(".gate").exists()).toBe(true);           // locked: permission missing
    await w.find(".gate button").trigger("click");
    expect(w.emitted("grantHotkeys")).toHaveLength(1);
  });
});

it('opens Audio controls from another settings tab', async () => {
  const wrapper = mount(SettingsView, {props:{apiKeyHint:''},slots:{'audio-controls':'<div>Shared audio controls</div>'}});
  await wrapper.findAll('.tabbtn').find(b=>b.text()==='System')!.trigger('click');
  await wrapper.vm.openAudioControls();
  expect(wrapper.get('[aria-label="Audio controls"]').text()).toContain('Shared audio controls');
  expect(wrapper.findAll('.tabbtn').find(b=>b.text()==='Audio')!.attributes('aria-pressed')).toBe('true');
});
