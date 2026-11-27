import { flushPromises, mount } from "@vue/test-utils";
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
    // The mic row is marked by its green edge alone; no "Mic" word.
    expect([a.classes("mic"), b.classes("mic"), b.find(".mic-recipient").exists()]).toEqual([false, true, false]);
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

  it("greys out ended tabs; every live row settles - the mic's too - and a Settled row restores", async () => {
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
    expect(gone.classes()).toContain("offline");
    // No Remove: a removed row would only come back as a settled one.
    expect(gone.get(".settle").text()).toBe("Restore");
    expect(live.get(".settle").attributes("tabindex")).toBe("0");

    await other.get(".settle").trigger("click");
    await live.get(".settle").trigger("keydown", { key: "Enter" });
    await gone.get(".settle").trigger("click");
    expect(wrapper.emitted("settle")).toEqual([["other"], ["live"]]);
    expect(wrapper.emitted("restore")).toEqual([["gone"]]);
    expect(wrapper.emitted("select")).toBeUndefined(); // the actions must not also select
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

  it("drags within a project only, sending the full order with other projects' slots untouched", async () => {
    const base = { offline_since: null, manual_pos: null };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a: "Alpha", web: "Website", b: "Beta", dead: "Dead spike" },
        meta: {
          a: { ...base, label: "Alpha", online: true, activated_at: 1, project: "studio" },
          web: { ...base, label: "Website", online: true, activated_at: 2, project: "website" },
          b: { ...base, label: "Beta", online: true, activated_at: 3, project: "studio" },
          dead: { ...base, label: "Dead spike", online: false, activated_at: 0, offline_since: 9, project: "studio" },
        },
        active: "a",
        viewed: "a",
        speaking: [],
        settledOpen: true,
      },
    });

    const row = (label: string) => wrapper.findAll("button.tab").find((b) => b.find(".tab-label").text() === label)!;
    await row("Alpha").trigger("dragstart");
    await row("Beta").trigger("drop");
    expect(wrapper.emitted("reorder")).toEqual([[["dead", "b", "web", "a"]]]);

    // Across projects, or onto Settled: ignored.
    await row("Alpha").trigger("dragstart");
    await row("Website").trigger("drop");
    await row("Alpha").trigger("dragstart");
    await row("Dead spike").trigger("drop");
    expect(wrapper.emitted("reorder")).toHaveLength(1);
    expect(row("Dead spike").attributes("draggable")).toBe("false");
  });

  it("treats agents without meta as online (legacy daemon)", () => {
    const wrapper = mount(AgentTabs, {
      props: { agents, active: "id-a", viewed: "id-a", speaking: [] },
    });

    const tabs = wrapper.findAll("button.tab");
    expect(tabs.every((t) => !t.classes().includes("offline"))).toBe(true);
  });

  it("shows each row's Tab hotkey number, and a row never moves because it works, speaks or queues", async () => {
    const props = {
      agents: { first: "First", second: "Second", extra: "Extra" },
      meta: {
        first: { label: "First", online: true, activated_at: 1, offline_since: null, shortcut: 1 },
        second: { label: "Second", online: true, activated_at: 2, offline_since: null, shortcut: 2 },
        extra: { label: "Extra", online: true, activated_at: 3, offline_since: null, shortcut: null },
      },
      active: null, viewed: null, speaking: [] as string[],
    };
    const wrapper = mount(AgentTabs, { props });
    const rows = () => wrapper.findAll("button.tab").map((b) => [b.find(".tab-label").text(), b.find(".shortcut").text()]);
    const quiet = [["First", "Tab 1"], ["Second", "Tab 2"], ["Extra", ""]];
    expect(rows()).toEqual(quiet);
    await wrapper.setProps({ thinking: ["first"], speaking: ["extra"], queued: { second: 2 } });
    expect(rows()).toEqual(quiet);
  });

  it("groups rows under project headings, no-project last, with branch and wait time on the row", () => {
    const base = { online: true, offline_since: null };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { notes: "Release notes", site: "Landing page", bare: "Legacy", fix: "Bug fixing" },
        meta: {
          notes: { ...base, activated_at: 1, label: "Release notes", project: "noisy-studio", branch: "main", waiting_since: 1000 - 240 },
          site: { ...base, activated_at: 2, label: "Landing page", project: "website", branch: "feat/cta" },
          bare: { ...base, activated_at: 3, label: "Legacy" },
          fix: { ...base, activated_at: 4, label: "Bug fixing", project: "noisy-studio", branch: "fix/hold" },
        },
        active: null, viewed: null, speaking: [], queued: { notes: 2, fix: 1 }, now: 1000,
      },
    });
    const list = wrapper.findAll(".project-head, button.tab").map((el) => el.classes().includes("project-head")
      ? { project: el.find(".project-name").text(), waiting: el.find(".project-waiting").text() }
      : { label: el.find(".tab-label").text(), where: el.find(".where").exists() ? el.find(".where").text() : null, waited: el.find(".waited").text() });
    expect(list).toEqual([
      { project: "noisy-studio", waiting: "3" },
      { label: "Release notes", where: "main", waited: "4m" },
      { label: "Bug fixing", where: "fix/hold", waited: "" },
      { project: "website", waiting: "" },
      { label: "Landing page", where: "feat/cta", waited: "" },
      { project: "No project", waiting: "" },
      { label: "Legacy", where: null, waited: "" },
    ]);
  });

  it("centres a row without a branch line, and keeps the wait time in the tooltip the hover actions cover", () => {
    const base = { online: true, offline_since: null };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { notes: "Release notes", bare: "Legacy" },
        meta: {
          notes: { ...base, activated_at: 1, label: "Release notes", project: "noisy-studio", branch: "main", waiting_since: 1000 - 240 },
          bare: { ...base, activated_at: 2, label: "Legacy" },
        },
        active: null, viewed: null, speaking: [], now: 1000,
      },
    });
    const [notes, bare] = wrapper.findAll("button.tab");
    expect([notes.classes("single"), bare.classes("single"), notes.attributes("title")]).toEqual([
      false, true, "Release notes · Ready · Waiting for you 4m",
    ]);
  });

  it("shows no project headings when the daemon knows no projects", () => {
    const wrapper = mount(AgentTabs, { props: { agents, active: "id-a", viewed: "id-a", speaking: [] } });
    expect(wrapper.find(".project-head").exists()).toBe(false);
  });

  it("marks the mic recipient with a green edge, not by moving it", () => {
    const wrapper = mount(AgentTabs, { props: { agents, active: "id-b", viewed: "id-a", speaking: [] } });
    expect(wrapper.findAll("button.tab").map((b) => b.classes().includes("mic"))).toEqual([false, true]);
  });

  it("folds ended sessions into a collapsed Settled section that names their project", async () => {
    localStorage.removeItem("noisy.tabs.settledOpen");
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { mine: "Release notes", gone: "Old spike" },
        meta: {
          mine: { label: "Release notes", online: true, activated_at: 1, offline_since: null, project: "noisy-studio" },
          gone: { label: "Old spike", online: false, activated_at: 0, offline_since: 5, project: "noisy-studio", branch: "spike" },
        },
        active: "mine", viewed: "mine", speaking: [], thinking: ["mine"], activity: { mine: "Bash · pytest" },
      },
    });
    const labels = () => wrapper.findAll("button.tab").map((b) => b.find(".tab-label").text());
    expect(labels()).toEqual(["Release notes"]);
    // Working is a glyph, the detail stays in the tooltip.
    expect(wrapper.get("button.tab").attributes("title")).toBe("Release notes · Receiving your speech · Working · Bash · pytest");

    const settled = wrapper.get("button.toggle");
    expect([settled.text(), settled.attributes("aria-expanded")]).toEqual(["▸ Settled 1", "false"]);
    await settled.trigger("click");
    expect(labels()).toEqual(["Release notes", "Old spike"]);
    expect(wrapper.findAll("button.tab")[1].find(".where").text()).toBe("noisy-studio · spike");
    expect(localStorage.getItem("noisy.tabs.settledOpen")).toBe("1");
    localStorage.removeItem("noisy.tabs.settledOpen");
  });

  it("lists settled conversations beside ended sessions, newest first, with the total and +N older", async () => {
    localStorage.removeItem("noisy.tabs.settledOpen");
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { live: "Release notes", gone: "Old spike" },
        meta: {
          live: { label: "Release notes", online: true, activated_at: 1, offline_since: null },
          gone: { label: "Old spike", online: false, activated_at: 0, offline_since: 50, project: "noisy-studio", branch: "spike" },
        },
        settledAgents: { total: 40, items: [
          { name: "hid", label: "Settled draft", project: "website", branch: "main", last_active_at: 90, ended: true, talk_key: "F13" },
        ] },
        active: "live", viewed: "live", speaking: [],
      },
    });
    expect(wrapper.get("button.toggle").text()).toBe("▸ Settled 41");
    await wrapper.get("button.toggle").trigger("click");

    const [, settledRow, endedRow] = wrapper.findAll("button.tab");
    expect([settledRow.get(".tab-label").text(), settledRow.get(".where").text(), settledRow.get(".shortcut").text()])
      .toEqual(["Settled draft", "website · main", "F13"]);
    expect(endedRow.get(".tab-label").text()).toBe("Old spike");
    expect(wrapper.get(".older").text()).toBe("+39 older");

    await settledRow.trigger("click"); // not in the list: it opens only once restored
    await settledRow.get(".settle").trigger("keydown", { key: " " });
    expect([wrapper.emitted("select"), wrapper.emitted("restore")]).toEqual([undefined, [["hid"]]]);
    localStorage.removeItem("noisy.tabs.settledOpen");
  });

  it("snoozes a row from the clock's menu and shows when a snoozed one comes back", async () => {
    const now = Math.floor(new Date(2026, 10, 25, 14, 30).getTime() / 1000);
    const back = Math.floor(new Date(2026, 10, 30, 9).getTime() / 1000);
    const wrapper = mount(AgentTabs, {
      attachTo: document.body,
      props: {
        agents: { live: "Release notes" },
        meta: { live: { label: "Release notes", online: true, activated_at: 1, offline_since: null } },
        settledAgents: { total: 1, items: [
          { name: "nap", label: "Pricing copy", project: "website", branch: null, last_active_at: 90, ended: false, talk_key: null, snoozed_until: back },
        ] },
        active: "live", viewed: "live", speaking: [], settledOpen: true, now,
      },
    });
    const [live, snoozed] = wrapper.findAll("button.tab");
    expect([snoozed.get(".where").text(), snoozed.find(".snooze").exists()]).toEqual(["snoozed until Mon 09:00 · website", false]);

    await live.get(".snooze").trigger("click");
    const options = wrapper.findAll("button.snooze-item");
    expect(options.map((option) => option.get("span").text())).toEqual(["1 hour", "3 hours", "6 hours", "Tomorrow", "Next week"]);
    await options[4].trigger("click");
    expect([wrapper.emitted("snooze"), wrapper.emitted("select"), wrapper.find(".snooze-menu").exists()])
      .toEqual([[["live", back]], undefined, false]);
    wrapper.unmount();
  });

  describe("folding a project", () => {
    const now = 10_000;
    const props = () => ({
      agents: { mic: "Release notes", busy: "Bug fixing", quiet: "Docs", talk: "QA", web: "Website" },
      meta: {
        mic: { label: "Release notes", online: true, activated_at: 1, offline_since: null, project: "studio", waiting_since: now - 5 * 60 },
        busy: { label: "Bug fixing", online: true, activated_at: 2, offline_since: null, project: "studio", waiting_since: now - 12 * 60 },
        quiet: { label: "Docs", online: true, activated_at: 3, offline_since: null, project: "studio" },
        talk: { label: "QA", online: true, activated_at: 4, offline_since: null, project: "studio" },
        web: { label: "Website", online: true, activated_at: 5, offline_since: null, project: "website" },
      },
      active: "mic", viewed: "web", speaking: ["talk"], queued: { busy: 2, quiet: 1 }, now,
    });
    const labels = (wrapper: ReturnType<typeof mount>) => wrapper.findAll("button.tab").map((b) => b.get(".tab-label").text());

    it("folds on a click, keeps the mic and speaking rows in sight, and sums up what waits", async () => {
      localStorage.removeItem("noisy.tabs.foldedProjects");
      const wrapper = mount(AgentTabs, { props: props() });
      const heading = () => wrapper.get(".project-head");

      await heading().trigger("click");

      expect(labels(wrapper)).toEqual(["Release notes", "QA", "Website"]);
      expect([heading().attributes("aria-expanded"), heading().get(".project-title .project-waiting").text(), heading().get(".folded-wait").text()])
        .toEqual(["false", "3", "12m"]);
      expect(localStorage.getItem("noisy.tabs.foldedProjects")).toBe('["studio"]');

      await heading().trigger("keydown", { key: "Enter" });
      expect([labels(wrapper).length, heading().get(".meta").text()]).toEqual([5, "3"]);
      localStorage.removeItem("noisy.tabs.foldedProjects");
    });

    it("keeps the viewed row in sight and remembers folded projects per browser", () => {
      localStorage.setItem("noisy.tabs.foldedProjects", '["website"]');
      const wrapper = mount(AgentTabs, { props: props() });
      expect(labels(wrapper)).toEqual(["Release notes", "Bug fixing", "Docs", "QA", "Website"]);
      expect(wrapper.findAll(".project-head")[1].attributes("aria-expanded")).toBe("false");
      localStorage.removeItem("noisy.tabs.foldedProjects");
    });

    it("does not fold when the heading was just dragged", async () => {
      const wrapper = mount(AgentTabs, { props: { ...props(), foldedProjects: [] } });
      const heading = wrapper.get(".project-head");
      await heading.trigger("dragstart");
      await heading.trigger("dragend");
      await heading.trigger("click");
      expect(heading.attributes("aria-expanded")).toBe("true");
    });
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

  it("shows each row's real hotkey, falling back to Tab N when it has none", () => {
    const base = { online: true, offline_since: null };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a: "A", b: "B" },
        meta: { a: { ...base, label: "A", activated_at: 1, shortcut: 1 }, b: { ...base, label: "B", activated_at: 2, shortcut: 2 } },
        active: null, viewed: null, speaking: [], tabKeys: { 1: "F16", 2: "" },
      },
    });

    expect(wrapper.findAll(".shortcut").map((k) => k.text())).toEqual(["F16", "Tab 2"]);
  });

  it("right-click captures a conversation's own talk key and shows a refusal", async () => {
    const base = { online: true, offline_since: null };
    const calls: [string, string][] = [];
    const setTalkKey = async (name: string, chord: string) => { calls.push([name, chord]); return chord === "f" ? "Already used by Hold" : null; };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a: "A", b: "B" },
        meta: { a: { ...base, label: "A", activated_at: 1, shortcut: 1 }, b: { ...base, label: "B", activated_at: 2, shortcut: null, talk_key: "F13" } },
        active: null, viewed: null, speaking: [], tabKeys: { 1: "F16" }, setTalkKey,
      },
      attachTo: document.body,
    });
    const keys = wrapper.findAll(".shortcut").map((k) => k.text());

    await wrapper.findAll("button.tab")[0].trigger("contextmenu");
    await wrapper.find(".keymenu-item").trigger("click");
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyF" }));
    await new Promise((r) => setTimeout(r, 400)); // the double-tap window
    await flushPromises();
    const problem = wrapper.find(".keymenu-problem").text();

    expect([keys, calls, problem]).toEqual([["F16", "F13"], [["a", "f"]], "Already used by Hold"]);
    wrapper.unmount();
  });

  it("drags a whole project onto another project's heading", async () => {
    const base = { online: true, offline_since: null };
    const wrapper = mount(AgentTabs, {
      props: {
        agents: { a1: "A1", b1: "B1" },
        meta: { a1: { ...base, label: "A1", activated_at: 1, manual_pos: 0, project: "alpha" }, b1: { ...base, label: "B1", activated_at: 2, manual_pos: 1, project: "beta" } },
        active: null, viewed: null, speaking: [],
      },
    });
    const [alpha, beta] = wrapper.findAll(".project-head");

    await beta.trigger("dragstart");
    await alpha.trigger("drop");

    expect(wrapper.emitted("reorder")).toEqual([[["b1", "a1"]]]);
  });
});

