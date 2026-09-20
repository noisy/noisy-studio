import type { Meta, StoryObj } from "@storybook/vue3";
import EngineChoice from "./EngineChoice.vue";
import type { ProvidersInfo } from "../api/client";
import { setProviderFixture } from "../storybook/daemon.fixture";

/* The first-contact engine cards (#36/#37).
 *
 * The gate's first question is now "which engine?", not "what's your key?".
 * These states are the ones a fresh user can actually land in — including
 * the one where the local path is a dead end and must say why.
 */

// Shared isolated provider state preserves each story’s download scenario.
const GROK = {
  name: "grok",
  kind: "cloud-api" as const,
  label: "Grok (xAI)",
  directions: ["tts", "stt"] as ("tts" | "stt")[],
  streaming: { tts: true, stt: true },
  ready: false,
  ready_detail: "No xAI API key yet — paste one below (console.x.ai → API Keys).",
  fields: [],
};

const LOCAL = {
  name: "local",
  kind: "local" as const,
  label: "Local (offline)",
  directions: ["tts", "stt"] as ("tts" | "stt")[],
  streaming: { tts: false, stt: false },
  ready: true,
  ready_detail: "",
  fields: [],
};

const meta: Meta<typeof EngineChoice> = {
  component: EngineChoice,
  title: "Dashboard/EngineChoice",
};
export default meta;

function story(info: ProvidersInfo | null): StoryObj<typeof EngineChoice> {
  return {
    render: () => ({
      components: { EngineChoice },
      setup: () => setProviderFixture(info),
      template: `<div style="max-width:560px"><EngineChoice /></div>`,
    }),
  };
}

/** Fresh install, cloud pre-selected: the classic key flow sits below. */
export const CloudPicked = story({
  catalog: [GROK, LOCAL],
  active: { tts: "grok", stt: "grok" },
  downloads: [],
});

/** LOCAL clicked, weights arriving: the gate itself shows the bars. */
export const LocalPickedDownloading = story({
  catalog: [GROK, LOCAL],
  active: { tts: "local", stt: "local" },
  downloads: [
    {
      name: "kokoro-v1.0.onnx", label: "Kokoro voice model (kokoro-v1.0.onnx)",
      state: "downloading", done_bytes: 210 * 1024 * 1024,
      total_bytes: 326 * 1024 * 1024, detail: "",
    },
    {
      name: "whisper-small", label: "Whisper model (small)",
      state: "downloading", done_bytes: 0, total_bytes: 0, detail: "",
    },
  ],
});

/** Everything on disk: the green line says the gate will close itself. */
export const LocalReady = story({
  catalog: [GROK, LOCAL],
  active: { tts: "local", stt: "local" },
  downloads: [
    {
      name: "kokoro-v1.0.onnx", label: "Kokoro voice model (kokoro-v1.0.onnx)",
      state: "done", done_bytes: 326 * 1024 * 1024,
      total_bytes: 326 * 1024 * 1024, detail: "",
    },
    { name: "whisper-small", label: "Whisper model (small)", state: "done",
      done_bytes: 0, total_bytes: 0, detail: "" },
  ],
});

/** Local can't run here — the card explains the remedy, not just "no". */
export const LocalNotReadyWithRemedy = story({
  catalog: [
    GROK,
    {
      ...LOCAL,
      ready: false,
      ready_detail: "faster-whisper is not installed — run: uv sync --extra local",
    },
  ],
  active: { tts: "local", stt: "local" },
  downloads: [],
});

/** A dead network mid-download: failure stays visible, RETRY at hand. */
export const DownloadFailed = story({
  catalog: [GROK, LOCAL],
  active: { tts: "local", stt: "local" },
  downloads: [
    {
      name: "kokoro-v1.0.onnx", label: "Kokoro voice model (kokoro-v1.0.onnx)",
      state: "error", done_bytes: 0, total_bytes: 0,
      detail: "connection reset by peer",
    },
  ],
});


export const PreparingBeforeApply: StoryObj<typeof EngineChoice> = {
  ...story({
    catalog:[GROK, LOCAL], active:{stt:'grok',tts:'grok'},
    downloads:[{name:'whisper-base',label:'Whisper base',state:'downloading',done_bytes:0,total_bytes:0,detail:''}],
  }),
  play: async ({canvasElement}) => {
    for (let attempt=0; attempt<30; attempt++) {
      const button=[...canvasElement.querySelectorAll('button')].find(b=>b.textContent?.includes('Local · Offline'));
      if (button) {button.click();return;}
      await new Promise(resolve=>setTimeout(resolve,30));
    }
  },
};
