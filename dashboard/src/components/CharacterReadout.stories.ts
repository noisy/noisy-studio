import type { Meta, StoryObj } from "@storybook/vue3";
import CharacterReadout from "./CharacterReadout.vue";
import HudPanel from "./HudPanel.vue";
import StatusStrip from "./StatusStrip.vue";

const meta: Meta = { title: "HUD/Character Settings" };
export default meta;

const character = { humor: 60, honesty: 80, verbosity: 60, talkative: 100, voice: "altair", speed: 1.15 };

// The editor on its own.
export const Content: StoryObj = {
  render: () => ({
    components: { CharacterReadout },
    setup: () => ({ character }),
    template: `<div style="max-width:330px"><CharacterReadout :character="character" /></div>`,
  }),
};

/** The stored values and displayed scales have the same direction (#108). */
export const VerbosityRange: StoryObj = {
  render: () => ({
    components: { CharacterReadout },
    setup: () => ({
      quiet: { ...character, verbosity: 0, talkative: 0 },
      expansive: { ...character, verbosity: 100, talkative: 100 },
    }),
    template: `<div style="display:flex;gap:48px">
      <div style="width:280px"><h3>Radio clicks, only when asked</h3><CharacterReadout :character="quiet" /></div>
      <div style="width:280px"><h3>Lecture, frequent updates</h3><CharacterReadout :character="expansive" /></div>
    </div>`,
  }),
};

// As it actually sits on the dashboard — inside a titled HudPanel.
export const InPanel: StoryObj = {
  render: () => ({
    components: { CharacterReadout, HudPanel },
    setup: () => ({ character }),
    template: `
      <div style="max-width:330px">
        <HudPanel index="04" title="CHARACTER SETTINGS">
          <CharacterReadout :character="character" />
        </HudPanel>
      </div>`,
  }),
};

// Inside the persona rail, which recolors --cyan → --violet. Regression
// guard: humor must stay BLUE here (it used to turn violet). If humor and
// talkative look identical, the fix regressed.
export const InPersonaRail: StoryObj = {
  name: "in persona rail (--cyan → --violet)",
  render: () => ({
    components: { CharacterReadout },
    setup: () => ({ character }),
    template: `
      <div style="max-width:330px; --cyan: var(--violet); --cyan-hi: var(--violet-hi); --cyan-dim: var(--violet-dim); --glow-cyan: var(--glow-violet); background: color-mix(in srgb, var(--violet) 6%, transparent); padding:14px">
        <CharacterReadout :character="character" />
      </div>`,
  }),
};

// StatusStrip lives here too (it shares the readout look); kept as a story.
export const Status: StoryObj = {
  render: () => ({
    components: { StatusStrip },
    setup: () => ({
      status: {
        listening: true, muted: false, recording: true, claude_speaking: false,
        speaking_agents: [], queued: 1, session_cost_usd: { user: 0.0021, claude: 0.0226 },
        credits_usd: 4.53, mode: "live", tts_mode: "live", end_silence_ms: 800, mic_sensitivity: 50,
        smart_turn: 0, smart_turn_mode: "soft", language: "pl", agents: {},
        agent_labels: {}, active_agent: null,
      },
    }),
    template: `<div style="max-width:330px"><StatusStrip :status="status" :offline="false" /></div>`,
  }),
};
