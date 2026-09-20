import type { Meta, StoryObj } from "@storybook/vue3";
import StatusView from "./StatusView.vue";
import { useSpeechFixture } from "../storybook/speech.fixture";

/** The status board's speech-to-text section, endpoint mocked - no daemon,
 *  no real transcriptions. Covers list, parallel running, pass and fail. */
const meta: Meta<typeof StatusView> = {
  title: "Dashboard/StatusView",
  component: StatusView,
  parameters: { layout: "fullscreen" },
};
export default meta;

const TESTS = {
  engine: "Grok STT",
  tests: [
    { file: "20260902-0624-u94.wav", seconds: 21.4,
      expected: "I would like to run those tests interactively." },
    { file: "20260902-0621-u88.wav", seconds: 2.9, expected: "" },
  ],
};

export const PassingRuns: StoryObj = {
  render: () => ({
    components: { StatusView },
    setup: () =>
      useSpeechFixture(TESTS, 800, ({ file, path }) => ({
        file, path, engine: "Grok STT", ms: 812,
        actual: "I would like to run those tests interactively.",
        expected: "I would like to run those tests interactively.",
        ratio: 1, ok: true,
      })),
    template: "<StatusView />",
  }),
};

export const FailingLivePipeline: StoryObj = {
  render: () => ({
    components: { StatusView },
    setup: () =>
      useSpeechFixture(TESTS, 1200, ({ file, path }) =>
        path === "live"
          ? { file, path, ms: 2400, ratio: 0.71, ok: false,
              actual: "I would like to run those Tests. Interactively.",
              expected: "I would like to run those tests interactively.",
              diff: "[-tests interactively.|+Tests. Interactively.]" }
          : { file, path, ms: 700, ratio: 1, ok: true,
              actual: "I would like to run those tests interactively.",
              expected: "I would like to run those tests interactively." },
      ),
    template: "<StatusView />",
  }),
};
