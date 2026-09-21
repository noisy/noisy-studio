import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AgentTabs from "./AgentTabs.vue";

const agents = { "id-a": "noisy-studio-stabilization", "id-b": "personal" };

describe("AgentTabs", () => {
  it.each([undefined, {
    "session-1": { label: "/private/example/session-1", online: true, activated_at: 1, offline_since: null },
  }])("hides path labels from legacy and metadata sources, including tooltips", async (meta) => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { "session-1": "/private/example/session-1" }, meta,
        active: "session-1", viewed: "session-1", speaking: [],
      },
    });

    const tab = wrapper.get("button");
    expect(tab.get(".tab-label").text()).toBe("New conversation");
    expect(tab.attributes("title")).not.toContain("/private/");
    await tab.trigger("click");
    expect(wrapper.emitted("select")).toEqual([["session-1"]]);
  });

  it("renders a labeled tab per agent", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    const labels = wrapper.findAll("button").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["noisy-studio-stabilization", "personal"]);
  });

  it("emits select with the agent id on click", async () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    await wrapper.findAll("button")[1].trigger("click");

    expect(wrapper.emitted("select")).toEqual([["id-b"]]);
  });

  it("marks viewing, speaking and thinking states in the fixed status slot", () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents,
        active: "id-b",
        viewed: "id-a",
        speaking: ["id-b"],
        thinking: ["id-a"],
      },
    });

    const [a, b] = wrapper.findAll("button");
    expect(a.classes()).toContain("viewing");
    expect(a.find(".mic-recipient").attributes("aria-hidden")).toBe("true");
    expect(b.find(".mic-recipient").attributes("aria-hidden")).toBe("false");
    expect(b.find(".mic-recipient").text()).toBe("Mic");
    expect(b.find(".eq").exists()).toBe(true); // speaking = green equalizer
    expect(a.find(".eq").exists()).toBe(false);
    expect(a.find(".dot.think").exists()).toBe(true); // working = violet pulse
    // The slot always exists, so state changes never resize the tab.
    expect(a.find(".statusslot").exists()).toBe(true);
    expect(b.find(".statusslot").exists()).toBe(true);
  });

  it("waiting count beats working, speaking beats the count", () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents,
        active: "id-a",
        viewed: "id-a",
        speaking: ["id-b"],
        thinking: ["id-a"],
        queued: { "id-a": 3, "id-b": 5 },
      },
    });

    const [a, b] = wrapper.findAll("button");
    expect(a.find(".waitcount").text()).toBe("3"); // queued outranks working
    expect(a.find(".dot.think").exists()).toBe(false);
    expect(b.find(".waitcount").exists()).toBe(false); // speaking still hides it
    expect(b.find(".eq").exists()).toBe(true);
  });

  it("mute always wins and carries its own dimmed count", () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents,
        active: "id-a",
        viewed: "id-a",
        speaking: ["id-a", "id-b"],
        muted: ["id-a", "id-b"],
        queued: { "id-b": 7 },
      },
    });

    const [a, b] = wrapper.findAll("button");
    expect(a.find(".mutespk").exists()).toBe(true); // muted, empty queue → red speaker
    expect(a.find(".eq").exists()).toBe(false); // mute beats speaking
    expect(b.find(".mutecount").text()).toBe("7"); // muted with backlog
    expect(b.find(".eq").exists()).toBe(false);
  });

  it("renders nothing without agents", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents: {}, active: null, viewed: null, speaking: [] },
    });

    expect(wrapper.find("nav").exists()).toBe(false);
  });

  it("groups actives first (arrival order), then offline (most recently ended first)", () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { old: "old", young: "young", dead1: "dead1", dead2: "dead2" },
        meta: {
          young: { label: "young", online: true, activated_at: 200, offline_since: null },
          old: { label: "old", online: true, activated_at: 100, offline_since: null },
          dead1: { label: "dead1", online: false, activated_at: 50, offline_since: 500 },
          dead2: { label: "dead2", online: false, activated_at: 60, offline_since: 900 },
        },
        active: "old",
        viewed: "old",
        speaking: [],
      },
    });

    const labels = wrapper.findAll("button").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["old", "young", "dead2", "dead1"]);
  });

  it("greys out ended tabs, and every tab can be closed - the mic's too", async () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { live: "live", other: "other", gone: "gone" },
        meta: {
          live: { label: "live", online: true, activated_at: 1, offline_since: null },
          other: { label: "other", online: true, activated_at: 2, offline_since: null },
          gone: { label: "gone", online: false, activated_at: 3, offline_since: 4 },
        },
        active: "live",
        viewed: "live",
        speaking: [],
      },
    });

    const [live, other, gone] = wrapper.findAll("button");
    expect(live.classes()).not.toContain("offline");
    // Every tab closes like a browser tab, including the one receiving the
    // mic (the daemon hands the mic on and says where it went).
    expect(live.find(".dismiss").exists()).toBe(true);
    expect(other.find(".dismiss").exists()).toBe(true);
    expect(gone.classes()).toContain("offline");

    await gone.find(".dismiss").trigger("click");
    await other.find(".dismiss").trigger("click");
    expect(wrapper.emitted("dismiss")).toEqual([["gone"], ["other"]]);
    expect(wrapper.emitted("select")).toBeUndefined(); // ✕ must not also select
  });

  it("puts user-pinned tabs first within their group, in pinned order", () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a: "a", b: "b", c: "c" },
        meta: {
          a: { label: "a", online: true, activated_at: 1, offline_since: null, manual_pos: null },
          b: { label: "b", online: true, activated_at: 2, offline_since: null, manual_pos: 1 },
          c: { label: "c", online: true, activated_at: 3, offline_since: null, manual_pos: 0 },
        },
        active: "a",
        viewed: "a",
        speaking: [],
      },
    });

    const labels = wrapper.findAll("button").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["c", "b", "a"]);
  });

  it("emits the group's new order after a drag within the group", async () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a: "a", b: "b", dead: "dead" },
        meta: {
          a: { label: "a", online: true, activated_at: 1, offline_since: null, manual_pos: null },
          b: { label: "b", online: true, activated_at: 2, offline_since: null, manual_pos: null },
          dead: { label: "dead", online: false, activated_at: 0, offline_since: 9, manual_pos: null },
        },
        active: "a",
        viewed: "a",
        speaking: [],
      },
    });

    const [a, b, dead] = wrapper.findAll("button");
    await a.trigger("dragstart");
    await b.trigger("drop");
    expect(wrapper.emitted("reorder")).toEqual([[["b", "a"]]]);

    // Dropping an active tab onto the offline group is ignored.
    await a.trigger("dragstart");
    await dead.trigger("drop");
    expect(wrapper.emitted("reorder")).toHaveLength(1);
  });

  it("treats agents without meta as online (legacy daemon)", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    const tabs = wrapper.findAll("button");
    expect(tabs.every((t) => !t.classes().includes("offline"))).toBe(true);
  });
});
