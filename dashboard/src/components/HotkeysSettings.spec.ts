import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import HotkeysSettings from "./HotkeysSettings.vue";

const pane = (title: string, action: string) => ({ title, bindings: [{ action, label: action, chord: "F8" }] });

describe("HotkeysSettings locked state", () => {
  it("keeps the GRANT banner clickable while the bindings are disabled", async () => {
    const w = mount(HotkeysSettings, {
      props: { permission: "missing", talk: pane("Push to talk", "hold"), tabs: pane("…to a specific tab", "tab1") },
    });
    // The root must not carry the dashboard's global .locked class (it
    // dims and blocks pointer events on the whole element).
    expect(w.find(".hotkeys").classes()).not.toContain("locked");
    expect(w.find(".hotkeys").classes()).toContain("perm-locked");
    expect(w.find("fieldset").attributes("disabled")).toBeDefined();
    await w.find(".gate button").trigger("click");
    expect(w.emitted("grant")).toHaveLength(1);
  });
});

describe("HotkeysSettings dictation card", () => {
  const dictate = (chord: string) => ({ title: "Dictate anywhere", bindings: [{ action: "dictate", label: "Dictate", chord }] });
  const base = { permission: "granted" as const, talk: pane("Push to talk", "hold"), tabs: pane("…to a specific tab", "tab1") };

  it("asks for Accessibility once a dictate key is bound", async () => {
    const w = mount(HotkeysSettings, { props: { ...base, dictate: dictate("F13"), accessibility: "missing" } });
    const gate = w.find(".card.dictate .gate");
    expect(gate.text()).toContain("Dictation cannot paste yet.");
    await gate.find("button").trigger("click");
    expect(w.emitted("grantAccessibility")).toHaveLength(1);
  });

  it("does not nag while no dictate key is bound, or once access is granted", () => {
    const unbound = mount(HotkeysSettings, { props: { ...base, dictate: dictate(""), accessibility: "missing" } });
    const granted = mount(HotkeysSettings, { props: { ...base, dictate: dictate("F13"), accessibility: "granted" } });
    expect([unbound.find(".card.dictate").exists(), unbound.find(".gate").exists(), granted.find(".gate").exists()])
      .toEqual([true, false, false]);
  });

  it("captures the dictate key like any other", async () => {
    const w = mount(HotkeysSettings, { props: { ...base, dictate: dictate("") } });
    await w.find(".card.dictate .chord").trigger("click");
    expect(w.emitted("capture")).toEqual([["dictate"]]);
  });
});
