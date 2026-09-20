import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { Character, DaemonStatus } from "../types";
import { speedFromAngle, traitValueFromAngle } from "./characterMath";
import CharacterReadout from "./CharacterReadout.vue";
import StatusStrip from "./StatusStrip.vue";
import { stateLabel } from "./systemState";

const character: Character = {
  humor: 50,
  honesty: 50,
  verbosity: 0,
  talkative: 100,
  voice: "altair",
  speed: 1.1,
};

describe("CharacterReadout", () => {
  it("shows the speed", () => {
    const wrapper = mount(CharacterReadout, { props: { character } });

    expect(wrapper.find(".sv").text()).toBe("1.10×");
  });

  it("emits the changed trait without changing other character values", async () => {
    const wrapper = mount(CharacterReadout, { props: { character } });
    await wrapper.get('input[aria-label="Humor"]').setValue('80');
    expect(wrapper.emitted('change')).toEqual([[{ humor: 80 }]]);
  });

  it('displays canonical verbosity directly without changing the character', () => {
    const wrapper = mount(CharacterReadout, { props: { character } });
    const slider = wrapper.get('input[aria-label="Verbosity"]');
    expect((slider.element as HTMLInputElement).value).toBe('0');
    expect(slider.attributes('aria-valuetext')).toBe('0 · clicks');
    expect(wrapper.emitted('change')).toBeUndefined();
  });

  it('sends the displayed verbosity unchanged to the backend', async () => {
    const wrapper = mount(CharacterReadout, { props: { character } });
    await wrapper.get('input[aria-label="Verbosity"]').setValue('80');
    expect(wrapper.emitted('change')).toEqual([[{ verbosity: 80 }]]);
    expect(wrapper.get('input[aria-label="Verbosity"]').attributes('aria-valuetext')).toBe('80 · generous');
  });

  it("emits the selected speech rate", async () => {
    const wrapper = mount(CharacterReadout, { props: { character } });
    await wrapper.get('input[aria-label="Speed"]').setValue('1.25');
    expect(wrapper.emitted('change')).toEqual([[{ speed: 1.25 }]]);
  });
});

describe("characterMath", () => {
  it("maps gauge angles across the 280° sweep to 0-100", () => {
    expect(traitValueFromAngle(130)).toBe(0); // arc start
    expect(traitValueFromAngle(270)).toBe(50); // halfway
    expect(traitValueFromAngle(50)).toBe(100); // arc end (130+280 mod 360)
  });

  it("snaps dead-zone angles to the nearest arc end", () => {
    expect(traitValueFromAngle(60)).toBe(100);
    expect(traitValueFromAngle(120)).toBe(0);
  });

  it("maps speed dial angles into the 0.7-1.5 range in 0.05 steps", () => {
    expect(speedFromAngle(145)).toBe(0.7);
    expect(speedFromAngle(270)).toBe(1.1);
    expect(speedFromAngle(35)).toBe(1.5);
  });
});


function status(overrides: Partial<DaemonStatus>): DaemonStatus {
  return {
    listening: true, muted: false, voice_muted: false, recording: false,
    claude_speaking: false, playing_utterance_id: 0,
    api_key_set: true, api_key_hint: "····1234",
    stt_latency_ms: null, tts_latency_ms: null, input_device: "", output_device: "system" as const,
    tab_audio: false, activity: {},
    speaking_agents: [], queued: 0, session_cost_usd: { user: 0.01, claude: 0.02 },
    usage: { stt_seconds: 0, tts_chars: 0 },
    credits_usd: 4.5, mode: "live", tts_mode: "live", end_silence_ms: 800, mic_sensitivity: 50,
    smart_turn: 0, smart_turn_mode: "soft", detection_mode: "auto", ptt_held: false,
    language: "pl", agents: {}, agent_labels: {}, active_agent: null,
    ...overrides,
  };
}

describe("stateLabel", () => {
  it.each([
    [null, true, "OFFLINE"],
    [status({ muted: true }), false, "MUTED"],
    [status({ listening: false }), false, "SPEAKING"],
    [status({ recording: true }), false, "RECORDING"],
    [status({}), false, "LISTENING"],
  ])("labels %#", (s, offline, expected) => {
    expect(stateLabel(s, offline).label).toBe(expected);
  });
});

describe("StatusStrip", () => {
  it("shows total cost and the credits fuel", () => {
    const wrapper = mount(StatusStrip, { props: { status: status({}), offline: false } });

    expect(wrapper.find(".total").text()).toBe("$0.0300");
    expect(wrapper.find(".fuel .frow b").text()).toBe("$4.50");
    expect(wrapper.findAll(".fuelbar i.off").length).toBe(2); // 4.5/5 → 18 of 20 on
  });
});
