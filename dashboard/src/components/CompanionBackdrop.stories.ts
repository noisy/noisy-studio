import type { Meta, StoryObj } from "@storybook/vue3";
import { computed, defineComponent, onUnmounted, ref, watch } from "vue";
import Companion, { type CompanionAgent, type CompanionMessage } from "./Companion.vue";

/* How the widget survives whatever is behind it.
 *
 * Floating over an editor it has no background of its own, so its contents
 * are read against unknown pixels - a dark theme, a light theme, a
 * screenshot, a photo. Anything that relies on the HUD's dark chrome to be
 * legible will fail somewhere on this slider.
 */
const meta: Meta = { title: "Widget/CompanionBackdrop" };
export default meta;

const FEED: CompanionMessage[] = [
  { id: 1, role: "claude", text: "I'm ready." },
  { id: 2, role: "user", text: "how does this look on a light background?" },
  {
    id: 3,
    role: "claude",
    text:
      "Drag the slider from black to white. What matters is whether the text stays " +
      "readable and the widget still reads as one object rather than pieces floating " +
      "on nothing.",
  },
];

const AGENTS: CompanionAgent[] = [
  { name: "stream-day-2", voice: "lux", active: true },
  { name: "chat", voice: "eve", unread: true },
];

/** Grey ramp plus a few real-world backdrops. */
const Backdrop = defineComponent({
  components: { Companion },
  setup() {
    const level = ref(10);
    const mode = ref<"grey" | "code" | "photo">("grey");
    const transparent = ref(true);

    const grey = computed(() => {
      const v = Math.round((level.value / 100) * 255);
      return `rgb(${v}, ${v}, ${v})`;
    });
    const background = computed(() => {
      if (mode.value === "code") {
        // A code editor is not flat: syntax colours are exactly the kind of
        // busy midtone that swallows an unbacked widget.
        return "repeating-linear-gradient(180deg, #1e1e2e 0 22px, #232338 22px 44px)";
      }
      if (mode.value === "photo") {
        return "linear-gradient(120deg, #ff9a3c, #6a5acd 45%, #0f9b8e)";
      }
      return grey.value;
    });

    watch(
      transparent,
      (on) => document.body.classList.toggle("companion-transparent", on),
      { immediate: true },
    );
    // The class lives on <body>, OUTSIDE this story's root - without this
    // cleanup it leaks into every story visited afterwards and renders
    // them in ghost/transparent mode (seen as "empty" sections).
    onUnmounted(() => document.body.classList.remove("companion-transparent"));

    return { level, mode, transparent, background, grey };
  },
  template: `
    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center;font:13px/1.5 var(--sans);
                  padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)">
        <strong>Preview</strong>
        <label>backdrop
          <input type="range" min="0" max="100" v-model.number="level"
                 :disabled="mode !== 'grey'" style="vertical-align:middle" />
          {{ mode === 'grey' ? grey : mode }}
        </label>
        <label><input type="radio" value="grey" v-model="mode" /> grey ramp</label>
        <label><input type="radio" value="code" v-model="mode" /> editor</label>
        <label><input type="radio" value="photo" v-model="mode" /> colourful</label>
        <label><input type="checkbox" v-model="transparent" /> transparent mode</label>
      </div>

      <div :style="{ background, padding: '28px', borderRadius: '10px' }">
        <div style="max-width:420px;margin:auto">
          <Companion mode="claude" voice="lux" :feed="FEED" :agents="AGENTS"
                     :max-height="200" />
        </div>
      </div>
    </div>
  `,
  data: () => ({ FEED, AGENTS }),
});

export const Slider: StoryObj = { render: () => Backdrop };
