import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { Utterance } from "../types";
import Bubble from "./Bubble.vue";
import { formatCost, replaySpeechText, statusChip } from "./bubbleStatus";
import AgentBubble from "./AgentBubble.vue";
import UserBubble from "./UserBubble.vue";

describe("statusChip", () => {
  it.each([
    ["user", "recording…", "rec", "● RECORDING"],
    ["user", "transcribing (live)…", "work", "◌ TRANSCRIBING"],
    ["user", "ready — awaiting pickup", "work", "◌ AWAITING AGENT"],
    ["user", "delivered to Claude", "done", "✓ DELIVERED"],
    ["user", "cancelled by you", "off", "✕ CANCELLED"],
    ["user", "transcription error", "fail", "✕ ERROR"],
    ["user", "dropped — too short", "fail", "✕ DROPPED"],
    ["claude", "queued", "work", "◌ QUEUED"],
    ["claude", "queued — waiting for you to finish", "work", "◌ HOLDING"],
    ["claude", "synthesizing (Grok TTS)…", "work", "◌ SYNTHESIZING"],
    ["claude", "playing through speakers…", "spoken", "▶ PLAYING"],
    ["claude", "played", "done", "✓ PLAYED"],
    ["claude", "unheard — voice muted", "off", "◌ UNHEARD"],
  ] as const)("maps %s %s → %s", (role, status, kind, label) => {
    expect(statusChip(status, role)).toEqual({ kind, label });
  });

  it("renders a status outside the machine's vocabulary raw", () => {
    expect(statusChip("reticulating splines…", "user")).toEqual({
      kind: "work",
      label: "RETICULATING SPLINES…",
    });
  });
});

describe("formatCost", () => {
  it("renders dollars with 4 decimals and em-dash for zero", () => {
    expect(formatCost(0.00412)).toBe("$0.0041");
    expect(formatCost(0)).toBe("—");
  });
});

describe("Bubble", () => {
  it.each([
    ["Hello there", ".md-p"],
    ["First paragraph\n\nLast paragraph", ".md-p:last-child"],
    ["- First item\n- Last item", ".md-ul li:last-child"],
  ])("keeps the live cursor inside the final text block: %s", (text, finalBlock) => {
    const wrapper = mount(Bubble, {
      props: { side: "left", accent: "amber", who: "You", text, live: true, statusKind: "rec", statusLabel: "", time: "" },
    });
    expect(wrapper.get(".caret").element.parentElement).toBe(wrapper.get(finalBlock).element);
  });
  it("keeps unheard speech explicit in the compact companion", () => {
    const wrapper = mount(Bubble, {
      props: { side: "right", accent: "violet", who: "Codex", text: "Ready to review.", compact: true, statusKind: "off", statusLabel: "Unheard", time: "" },
    });
    expect(wrapper.get(".compact-label").text()).toContain("Unheard");
  });
  it("renders who, text, status label and cost", () => {
    const wrapper = mount(Bubble, {
      props: {
        side: "left" as const,
        accent: "violet" as const,
        who: "CLAUDE",
        text: "Done. Staging is live.",
        statusKind: "done" as const,
        statusLabel: "✓ PLAYED",
        time: "21:46:38",
        cost: "$0.0041",
      },
    });

    expect(wrapper.find(".who").text()).toBe("CLAUDE");
    expect(wrapper.find(".txt").text()).toContain("Done. Staging is live.");
    expect(wrapper.find(".st").text()).toBe("✓ PLAYED");
    expect(wrapper.find(".cost").text()).toBe("$0.0041");
    expect(wrapper.find(".livebars").exists()).toBe(false);
  });
});

describe("replaySpeechText", () => {
  it("recovers plain speech text from a claude card", () => {
    expect(replaySpeechText("„Cześć, **świecie**!”")).toBe("Cześć, **świecie**!");
    expect(replaySpeechText("[altair] „Cześć!”")).toBe("Cześć!"); // legacy cards
    expect(replaySpeechText("plain text without wrapper")).toBe("plain text without wrapper");
  });
});

describe("AgentBubble replay", () => {
  const played: Utterance = {
    id: 9,
    role: "claude",
    status: "played",
    text: "[altair] „Gotowe, wszystko zielone.”",
    detail: "",
    cost_usd: 0.001,
    agent: null,
    started_at: 0,
    updated_at: 0,
    committed_at: 0,
  };

  it("shows the replay icon on played speech and emits the utterance", async () => {
    const wrapper = mount(AgentBubble, { props: { utterance: played } });

    await wrapper.find(".replay").trigger("click");

    expect(wrapper.emitted("replay")).toEqual([[played]]);
  });

  it("offers no replay while still synthesizing", () => {
    const wrapper = mount(AgentBubble, {
      props: { utterance: { ...played, status: "synthesizing (Grok TTS)…", text: "" } },
    });

    expect(wrapper.find(".replay").exists()).toBe(false);
  });
});

describe("UserBubble", () => {
  const utterance: Utterance = {
    id: 7,
    role: "user",
    status: "recording…",
    text: "No dobra, to teraz",
    detail: "",
    cost_usd: 0,
    agent: null,
    started_at: 1_783_890_000,
    updated_at: 1_783_890_003,
    committed_at: 0,
  };

  it("explains the required action above the transcript and removes it after delivery", async () => {
    const explanation = "Type and send any message to reconnect. No special command is needed.";
    const wrapper = mount(UserBubble, { props: { utterance: {
      ...utterance, status: "unavailable — action needed", delivery_detail: explanation,
    } } });
    expect(wrapper.get(".st").text()).toBe("! ACTION NEEDED");
    expect(wrapper.get(".delivery-notice").text()).toBe(explanation);
    expect(wrapper.get(".delivery-notice").element.nextElementSibling).toBe(wrapper.get(".txt").element);
    expect(wrapper.get(".mfoot").text()).not.toContain(explanation);
    await wrapper.setProps({ utterance: { ...utterance, status: "delivered to Claude" } });
    expect(wrapper.find(".delivery-notice").exists()).toBe(false);
  });

  it("offers cancel only while awaiting Claude and emits the utterance", async () => {
    const awaiting = { ...utterance, status: "ready — awaiting pickup" };
    const wrapper = mount(UserBubble, { props: { utterance: awaiting } });

    await wrapper.find(".cancel").trigger("click");

    expect(wrapper.emitted("cancel")).toEqual([[awaiting]]);
    expect(
      mount(UserBubble, { props: { utterance } }).find(".cancel").exists(),
    ).toBe(false);
  });

  it("maps a recording utterance to a live amber bubble on the left", () => {
    const wrapper = mount(UserBubble, { props: { utterance } });

    expect(wrapper.find(".msg").classes()).toContain("side-left");
    expect(wrapper.find(".msg").classes()).toContain("accent-amber");
    expect(wrapper.find(".st").classes()).toContain("rec");
    expect(wrapper.find(".livebars").exists()).toBe(true);
  });
});
