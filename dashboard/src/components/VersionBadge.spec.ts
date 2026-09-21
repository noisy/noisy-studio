import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import VersionBadge from "./VersionBadge.vue";

describe("VersionBadge", () => {
  it("shows one quiet version when UI and daemon agree", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.8.0", daemonVersion: "2.8.0" },
    });

    expect(wrapper.find(".ver").text()).toBe("v2.8.0");
    expect(wrapper.find(".verskew").exists()).toBe(false);
  });

  it("tells the user to hard-refresh when the daemon is newer", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.7.7", daemonVersion: "2.8.0" },
    });

    expect(wrapper.find(".verskew").text()).toContain("HARD-REFRESH");
  });

  it("names the platform's own hard-refresh shortcut", () => {
    const cases = [
      { platform: "mac" as const, keys: "⌘⇧R" },
      { platform: "windows" as const, keys: "Ctrl+Shift+R" },
      { platform: "linux" as const, keys: "Ctrl+Shift+R" },
    ];
    for (const { platform, keys } of cases) {
      const wrapper = mount(VersionBadge, {
        props: { uiVersion: "2.7.7", daemonVersion: "2.8.0", platform },
      });
      expect(wrapper.find(".verskew").text()).toContain(keys);
    }
  });

  it("tells the user to update the native app when the UI is newer", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.8.0", daemonVersion: "2.7.7" },
    });

    expect(wrapper.find(".verskew").text()).toContain("UPDATE THE NOISY STUDIO APP");
  });

  it("compares numerically, not lexicographically (2.10.0 > 2.8.0)", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.8.0", daemonVersion: "2.10.0" },
    });

    expect(wrapper.find(".verskew").text()).toContain("HARD-REFRESH");
  });

  it("on a dev instance a stale daemon asks for a restart, not a native app update", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.9.0", daemonVersion: "2.8.0", devInstance: true },
    });

    expect(wrapper.find(".verskew").text()).toContain("RESTART THE DEV DAEMON");
    expect(wrapper.find(".verskew").text()).not.toContain("UPDATE THE NOISY STUDIO APP");
  });

  it("announces a newer published release in calm green", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.8.0", daemonVersion: "2.8.0", latestVersion: "2.9.0" },
    });

    expect(wrapper.find(".verupdate").text()).toContain("NEW v2.9.0");
    expect(wrapper.find(".verskew").exists()).toBe(false);
  });

  it("skew outranks the update announcement — fix inconsistency first", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.7.7", daemonVersion: "2.8.0", latestVersion: "2.9.0" },
    });

    expect(wrapper.find(".verskew").exists()).toBe(true);
    expect(wrapper.find(".verupdate").exists()).toBe(false);
  });

  it("stays quiet when the latest release is what we already run", () => {
    const wrapper = mount(VersionBadge, {
      props: { uiVersion: "2.8.0", daemonVersion: "2.8.0", latestVersion: "2.8.0" },
    });

    expect(wrapper.find(".ver").text()).toBe("v2.8.0");
  });

  it("stays quiet without a daemon version or on a dev install", () => {
    for (const daemonVersion of [null, "dev"]) {
      const wrapper = mount(VersionBadge, {
        props: { uiVersion: "2.8.0", daemonVersion },
      });
      expect(wrapper.find(".verskew").exists()).toBe(false);
      expect(wrapper.find(".ver").text()).toBe("v2.8.0");
    }
  });
});
