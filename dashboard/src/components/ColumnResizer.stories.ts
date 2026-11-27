import type { Meta, StoryObj } from "@storybook/vue3";
import { ref } from "vue";
import ColumnResizer from "./ColumnResizer.vue";
import { clampColumnWidth, COLUMN_WIDTH_LIMITS } from "../composables/useColumnWidth";

const meta: Meta<typeof ColumnResizer> = { title: "Dashboard/ColumnResizer", component: ColumnResizer };
export default meta;

/** Drag the edge between the two columns, or focus it and use the arrows. */
export const BetweenColumns: StoryObj<typeof ColumnResizer> = {
  render: () => ({
    components: { ColumnResizer },
    setup() {
      const width = ref<number>(COLUMN_WIDTH_LIMITS.default);
      return { width, resize: (px: number) => (width.value = clampColumnWidth(px)), reset: () => (width.value = COLUMN_WIDTH_LIMITS.default) };
    },
    template: `<div style="position:relative; display:grid; grid-template-columns:var(--left-column-width) 1fr; gap:20px; height:320px" :style="{ '--left-column-width': width + 'px' }">
      <ColumnResizer :width="width" @resize="resize" @reset="reset" />
      <div style="background:var(--surface-hover); border-radius:8px; padding:12px">Conversations · {{ width }} px</div>
      <div style="background:var(--surface-hover); border-radius:8px; padding:12px">Conversation</div>
    </div>`,
  }),
};
