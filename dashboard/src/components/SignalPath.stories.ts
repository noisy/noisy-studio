import type { Meta, StoryObj } from "@storybook/vue3";
import SignalPath from "./SignalPath.vue";
import type { ProvidersInfo } from "../api/client";
import { setProviderFixture } from "../storybook/daemon.fixture";

/* The wired provider chooser — concept D from ProviderChooserConcepts,
 * picked because the benchmarks made mixing the BEST configuration:
 * local hearing (faster than the cloud round-trip) + cloud speaking
 * (~5 s per reply locally). The pills make that mix legible.
 */

// Shared isolated provider state preserves each story’s download scenario.
const GROK = {
  name: "grok",
  kind: "cloud-api" as const,
  label: "Grok (xAI)",
  directions: ["tts", "stt"] as ("tts" | "stt")[],
  streaming: { tts: true, stt: true },
  ready: true,
  ready_detail: "",
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
  fields: [
    {
      key: "stt_model", kind: "choice" as const, label: "Whisper model",
      required: false, options: ["tiny", "base", "small", "medium", "large-v3"],
      value: "base",
    },
    {
      key: "tts_voice", kind: "choice" as const, label: "Kokoro voice",
      required: false, options: ["af_sarah", "af_heart", "am_adam", "bf_emma"],
      value: "af_sarah",
    },
  ],
};

const KOKORO_DONE = {
  name: "kokoro-v1.0.onnx", label: "Kokoro voice model (kokoro-v1.0.onnx)",
  state: "done" as const, done_bytes: 326 * 1024 * 1024,
  total_bytes: 326 * 1024 * 1024, detail: "",
};
const WHISPER_DONE = {
  name: "whisper-base", label: "Whisper model (base)", state: "done" as const,
  done_bytes: 0, total_bytes: 0, detail: "",
};

const meta: Meta<typeof SignalPath> = { component: SignalPath, title: "Dashboard/SignalPath" };
export default meta;

function story(info: ProvidersInfo | null): StoryObj<typeof SignalPath> {
  return {
    render: () => ({
      components: { SignalPath },
      setup: () => setProviderFixture(info),
      template: `<div style="max-width:720px"><SignalPath /></div>`,
    }),
  };
}

/** The benchmark-optimal mix: local ears, cloud voice. */
export const MixedDefault = story({
  catalog: [GROK, LOCAL],
  active: { tts: "grok", stt: "local" },
  downloads: [WHISPER_DONE],
});

/** Cloud both ways — the classic keyed setup, nothing under the pills. */
export const AllCloud = story({
  catalog: [GROK, LOCAL],
  active: { tts: "grok", stt: "grok" },
  downloads: [],
});

/** Fully local: honest ~5 s latency copy under the speaking pill. */
export const AllLocal = story({
  catalog: [GROK, LOCAL],
  active: { tts: "local", stt: "local" },
  downloads: [KOKORO_DONE, WHISPER_DONE],
});

/** A weight mid-flight under its own pill. */
export const Downloading = story({
  catalog: [GROK, LOCAL],
  active: { tts: "local", stt: "local" },
  downloads: [
    {
      name: "kokoro-v1.0.onnx", label: "Kokoro voice model (kokoro-v1.0.onnx)",
      state: "downloading", done_bytes: 200 * 1024 * 1024,
      total_bytes: 326 * 1024 * 1024, detail: "",
    },
    WHISPER_DONE,
  ],
});

/** A failed fetch stays visible with RETRY, under the right pill. */
export const DownloadFailed = story({
  catalog: [GROK, LOCAL],
  active: { tts: "local", stt: "grok" },
  downloads: [
    {
      name: "kokoro-v1.0.onnx", label: "Kokoro voice model (kokoro-v1.0.onnx)",
      state: "error", done_bytes: 0, total_bytes: 0,
      detail: "connection reset by peer",
    },
  ],
});

/** A selected engine that can't run says why, under the path. */
export const NotReadyWithRemedy = story({
  catalog: [
    { ...GROK, ready: false, ready_detail: "No xAI API key yet — paste one below (console.x.ai → API Keys)." },
    LOCAL,
  ],
  active: { tts: "grok", stt: "local" },
  downloads: [WHISPER_DONE],
});

/** An old daemon without /providers: the section hides, no error. */
export const OldDaemon = story(null);
