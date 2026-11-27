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

    const tab = wrapper.get("button.tab");
    expect(tab.get(".tab-label").text()).toBe("New conversation");
    expect(tab.attributes("title")).not.toContain("/private/");
    await tab.trigger("click");
    expect(wrapper.emitted("select")).toEqual([["session-1"]]);
  });

  it("renders a labeled tab per agent", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    const labels = wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["noisy-studio-stabilization", "personal"]);
  });

  it("emits select with the agent id on click", async () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    await wrapper.findAll("button.tab")[1].trigger("click");

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

    const [a, b] = wrapper.findAll("button.tab");
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

    const [a, b] = wrapper.findAll("button.tab");
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

    const [a, b] = wrapper.findAll("button.tab");
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
        agents: { old: "old title", young: "young title", dead1: "dead1 title", dead2: "dead2 title" },
        meta: {
          young: { label: "young title", online: true, activated_at: 200, offline_since: null },
          old: { label: "old title", online: true, activated_at: 100, offline_since: null },
          dead1: { label: "dead1 title", online: false, activated_at: 50, offline_since: 500 },
          dead2: { label: "dead2 title", online: false, activated_at: 60, offline_since: 900 },
        },
        active: "old",
        viewed: "old",
        speaking: [],
        settledOpen: true,
      },
    });

    const labels = wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["old title", "young title", "dead2 title", "dead1 title"]);
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
        settledOpen: true,
      },
    });

    const [live, other, gone] = wrapper.findAll("button.tab");
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
        agents: { a: "a title", b: "b title", c: "c title" },
        meta: {
          a: { label: "a title", online: true, activated_at: 1, offline_since: null, manual_pos: null },
          b: { label: "b title", online: true, activated_at: 2, offline_since: null, manual_pos: 1 },
          c: { label: "c title", online: true, activated_at: 3, offline_since: null, manual_pos: 0 },
        },
        active: "a",
        viewed: "a",
        speaking: [],
      },
    });

    const labels = wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["c title", "b title", "a title"]);
  });

  it("emits the section's new order after a drag within the section", async () => {
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
        settledOpen: true,
      },
    });

    const [a, b, dead] = wrapper.findAll("button.tab");
    await a.trigger("dragstart");
    await b.trigger("drop");
    expect(wrapper.emitted("reorder")).toEqual([[["b", "a"]]]);

    // Dropping an active tab onto the Settled section is ignored.
    await a.trigger("dragstart");
    await dead.trigger("drop");
    expect(wrapper.emitted("reorder")).toHaveLength(1);
  });

  it("treats agents without meta as online (legacy daemon)", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    const tabs = wrapper.findAll("button.tab");
    expect(tabs.every((t) => !t.classes().includes("offline"))).toBe(true);
  });

  it("shows each row's Tab hotkey number from the daemon, whatever section it is in", () => {
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { first: "First", second: "Second", extra: "Extra" },
        meta: {
          first: { label: "First", online: true, activated_at: 1, offline_since: null, shortcut: 1 },
          second: { label: "Second", online: true, activated_at: 2, offline_since: null, shortcut: 2 },
          extra: { label: "Extra", online: true, activated_at: 3, offline_since: null, shortcut: null },
        },
        active: null, viewed: null, speaking: [], thinking: ["first"], working: ["first"],
      },
    });
    const rows = wrapper.findAll("button.tab").map((b) => [b.find(".tab-label").text(), b.find(".shortcut").text()]);
    expect(rows).toEqual([["Second", "2"], ["Extra", ""], ["First", "1"]]);
  });

  it("shows project, branch and how long it waited, and leaves them out when unknown", () => {
    const base = { online: true, activated_at: 1, offline_since: null };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { known: "Release notes", bare: "Legacy" },
        meta: {
          known: { ...base, label: "Release notes", project: "noisy-studio", branch: "main", waiting_since: 1000 - 240 },
          bare: { ...base, label: "Legacy", activated_at: 2 },
        },
        active: null, viewed: null, speaking: [], now: 1000,
      },
    });
    const rows = wrapper.findAll("button.tab").map((b) => ({
      project: b.find(".project").exists() ? b.find(".project .clip").text() : null,
      label: b.find(".tab-label").text(),
      branch: b.find(".branch").exists() ? b.find(".branch").text() : null,
      waited: b.find(".waited").text(),
    }));
    expect(rows).toEqual([
      { project: "noisy-studio", label: "Release notes", branch: "main", waited: "4m" },
      { project: null, label: "Legacy", branch: null, waited: "" },
    ]);
  });

  it("splits the list into your turn, Working and a collapsed Settled section", async () => {
    localStorage.removeItem("noisy.tabs.settledOpen");
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { mine: "Release notes", busy: "Bug fixing", gone: "Old spike" },
        meta: {
          mine: { label: "Release notes", online: true, activated_at: 1, offline_since: null },
          busy: { label: "Bug fixing", online: true, activated_at: 2, offline_since: null },
          gone: { label: "Old spike", online: false, activated_at: 0, offline_since: 5 },
        },
        active: "mine", viewed: "mine", speaking: [],
        thinking: ["busy"], working: ["busy"], activity: { busy: "Bash · pytest" },
      },
    });
    const labels = () => wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text());
    expect(labels()).toEqual(["Release notes", "Bug fixing"]);
    expect(wrapper.find(".section").text()).toBe("▸ Working 1");
    expect(wrapper.find(".section").attributes("aria-expanded")).toBe("true");
    // A one-line glimpse of a shell command told nothing: the row says only
    // that it works; the detail stays in the tooltip.
    const busyRow = wrapper.findAll("button.tab")[1];
    expect([busyRow.find(".activity").exists(), busyRow.attributes("title")]).toEqual([false, "Bug fixing · Working · Bash · pytest"]);

    const settled = wrapper.findAll("button.toggle")[1];
    expect(settled.attributes("aria-expanded")).toBe("false");
    await settled.trigger("click");
    expect(labels()).toEqual(["Release notes", "Bug fixing", "Old spike"]);
    expect(localStorage.getItem("noisy.tabs.settledOpen")).toBe("1");
  });

  it("opens Settled when this browser remembered it open", () => {
    localStorage.setItem("noisy.tabs.settledOpen", "1");
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { live: "Release notes", gone: "Old spike" },
        meta: {
          live: { label: "Release notes", online: true, activated_at: 1, offline_since: null },
          gone: { label: "Old spike", online: false, activated_at: 0, offline_since: 5 },
        },
        active: "live", viewed: "live", speaking: [],
      },
    });
    expect(wrapper.get("button.toggle").attributes("aria-expanded")).toBe("true");
    expect(wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text())).toEqual(["Release notes", "Old spike"]);
    localStorage.removeItem("noisy.tabs.settledOpen");
  });

  it("folds Working on click, remembers it, and keeps the viewed row in sight", async () => {
    localStorage.removeItem("noisy.tabs.workingOpen");
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a: "Release notes", b: "Bug fixing", c: "Docs pass" },
        active: "a", viewed: "b", speaking: [], thinking: ["b", "c"], working: ["b", "c"],
      },
    });
    const labels = () => wrapper.findAll("button.tab").map((t) => t.find(".tab-label").text());
    expect(labels()).toEqual(["Release notes", "Bug fixing", "Docs pass"]);
    await wrapper.get("button.toggle").trigger("click");
    expect(wrapper.get("button.toggle").attributes("aria-expanded")).toBe("false");
    expect(labels()).toEqual(["Release notes", "Bug fixing"]);
    expect(localStorage.getItem("noisy.tabs.workingOpen")).toBe("0");
    localStorage.removeItem("noisy.tabs.workingOpen");
  });

  it("brings a working conversation back to the top when it has something for you", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [], thinking: ["id-a", "id-b"], working: ["id-a", "id-b"], queued: { "id-b": 1 } },
    });
    const labels = wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text());
    expect(labels).toEqual(["personal", "noisy-studio-stabilization"]);
  });
});
