import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import OrgTree from "./OrgTree.vue";
import { BENCH, LEGACY, NOW, STUDIO } from "./fixtures";

const mountTree = (props: Partial<InstanceType<typeof OrgTree>["$props"]> = {}) =>
  mount(OrgTree, { props: { projects: [STUDIO], now: NOW, micId: "studio", viewedId: "studio", ...props }, attachTo: document.body });

describe("OrgTree", () => {
  it("marks only the mic recipient with the mic slot", () => {
    const wrapper = mountTree({ projects: [STUDIO, LEGACY] });
    expect(wrapper.findAll(".manager").map((row) => [row.find(".title").text(), row.classes("mic"), row.find(".mic-slot svg").exists()]))
      .toEqual([["Studio manager", true, true], ["fitatu", false, false]]);
    wrapper.unmount();
  });

  it("shows what waits for you as the project's count, and the over-cap meter", () => {
    const wrapper = mountTree({ projects: [STUDIO, BENCH] });
    expect(wrapper.findAll(".project").map((project) => [project.find(".pill").text(), project.find(".usage").classes("over")]))
      .toEqual([["2", false], ["2", true]]);
    wrapper.unmount();
  });

  it("emits the CEO's actions with the ids they act on", async () => {
    const wrapper = mountTree();
    await wrapper.find(".manager .actions button:not([data-snooze-toggle])").trigger("click");
    const agents = wrapper.findAll(".agent");
    await agents[0].find('button[aria-label="Pause"]').trigger("click");
    await agents[1].find('button[aria-label="Stop"]').trigger("click");
    await agents[2].find("button.word").trigger("click");
    await wrapper.find(".header .hactions button").trigger("click");
    expect([wrapper.emitted("settle"), wrapper.emitted("pause"), wrapper.emitted("stop"), wrapper.emitted("review"), wrapper.emitted("focus")])
      .toEqual([[["studio"]], [["s1"]], [["s2"]], [["s3"]], [[STUDIO.id, true]]]);
    wrapper.unmount();
  });

  it("opens the snooze menu from the row and emits the chosen wake time", async () => {
    const wrapper = mountTree();
    await wrapper.find("[data-snooze-toggle]").trigger("click");
    await wrapper.find('.menu-overlay button[role="menuitem"]').trigger("click");
    expect([wrapper.emitted("snooze"), wrapper.find(".menu-overlay").exists()]).toEqual([[["studio", NOW + 3600]], false]);
    wrapper.unmount();
  });

  it("folds finished agents until asked", async () => {
    const wrapper = mountTree();
    const titles = () => wrapper.findAll(".agent .title").map((title) => title.text());
    const before = titles();
    await wrapper.find("button.more").trigger("click");
    expect([before, titles()]).toEqual([
      ["Org tree lab", "TestFlight upload", "Settle button spec"],
      ["Org tree lab", "TestFlight upload", "Settle button spec", "Bump versions"],
    ]);
    wrapper.unmount();
  });
});
