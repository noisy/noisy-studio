import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import HeaderVoiceControls from "./HeaderVoiceControls.vue";
import type { DaemonStatus } from "../types";

const status = (patch: Partial<DaemonStatus>) => ({ detection_mode: "auto", muted: false, ptt_held: false, voice_muted: false, ...patch }) as DaemonStatus;
const mic = (w: ReturnType<typeof mount>) => w.get("button.mic");
// The meter draws on a canvas, which the test DOM does not provide.
const global = { stubs: { Oscilloscope: true } };

describe("HeaderVoiceControls", () => {
  it("draws the global talk hotkey on the mic button: toggle first, else hold, else nothing", () => {
    const keyOf = (hotkeys: DaemonStatus["hotkeys"]) =>
      mount(HeaderVoiceControls, { props: { status: status({ hotkeys }), offline: false, level: 0 }, global }).find("button.mic .keycap");
    const hk = (bindings: Record<string, string>) => ({ configured: true, permission: "granted", armed: true, bindings, stored: {} }) as DaemonStatus["hotkeys"];

    expect([keyOf(hk({ toggle: "F15", hold: "F8" })).text(), keyOf(hk({ hold: "ctrl+alt+h" })).text(), keyOf(hk({})).exists()]).toEqual(["F15", "⌃⌥H", false]);
  });


  it("mutes the mic with a click in Auto", async () => {
    const w = mount(HeaderVoiceControls, { props: { status: status({}), offline: false, level: 0.4 }, global });
    expect(mic(w).text()).toBe("Mute mic");
    await mic(w).trigger("click");
    expect(w.emitted("toggleMute")).toHaveLength(1);
  });

  it("turns the same slot into Hold to talk in push to talk, with no mute", async () => {
    const w = mount(HeaderVoiceControls, { props: { status: status({ detection_mode: "ptt" }), offline: false, level: 0.4 }, global });
    expect(mic(w).text()).toBe("Hold to talk");
    await mic(w).trigger("pointerdown");
    await mic(w).trigger("pointerup");
    await mic(w).trigger("click");
    expect(w.emitted("pttStart")).toHaveLength(1);
    expect(w.emitted("pttStop")).toHaveLength(1);
    expect(w.emitted("toggleMute")).toBeUndefined();
    await w.setProps({ status: status({ detection_mode: "ptt", ptt_held: true }) });
    expect(mic(w).text()).toBe("◉ On air");
  });

  it("ends the hold on release even when the mic got muted mid-hold", async () => {
    const w = mount(HeaderVoiceControls, { props: { status: status({ detection_mode: "ptt" }), offline: false, level: 0.4 }, global });
    await mic(w).trigger("pointerdown");
    await w.setProps({ status: status({ detection_mode: "ptt", muted: true }) });
    await mic(w).trigger("pointerup");
    expect(w.emitted("pttStop")).toHaveLength(1);
  });

  it("offers an unmute when a mute is left over from Auto, instead of a dead hold button", async () => {
    const w = mount(HeaderVoiceControls, { props: { status: status({ detection_mode: "ptt", muted: true }), offline: false, level: 0.4 }, global });
    expect(mic(w).text()).toBe("Mic muted");
    await mic(w).trigger("pointerdown");
    await mic(w).trigger("click");
    expect(w.emitted("pttStart")).toBeUndefined();
    expect(w.emitted("toggleMute")).toHaveLength(1);
  });

  it("mutes all agents from the output group and disables everything offline", async () => {
    const w = mount(HeaderVoiceControls, { props: { status: status({ voice_muted: true }), offline: false, level: 0 }, global });
    const agents = w.get("button.agents");
    expect(agents.text()).toBe("Agents muted");
    await agents.trigger("click");
    expect(w.emitted("toggleAgentsMute")).toHaveLength(1);
    await w.setProps({ offline: true });
    expect(mic(w).text()).toBe("Mic offline");
    expect(w.findAll("button").every((b) => b.attributes("disabled") !== undefined)).toBe(true);
  });
});
