import { ref } from "vue";

/** A user-resizable column width, clamped and remembered per browser. */
export const COLUMN_WIDTH_LIMITS = { min: 220, max: 560, default: 268, step: 16 } as const;
const STORAGE_KEY = "noisy.layout.leftColumnPx";

export function clampColumnWidth(px: number): number {
  return Math.round(Math.min(COLUMN_WIDTH_LIMITS.max, Math.max(COLUMN_WIDTH_LIMITS.min, px)));
}

function storedWidth(): number {
  try {
    const saved = Number(localStorage.getItem(STORAGE_KEY));
    return saved ? clampColumnWidth(saved) : COLUMN_WIDTH_LIMITS.default;
  } catch { return COLUMN_WIDTH_LIMITS.default; }
}

export function useColumnWidth() {
  const width = ref(storedWidth());
  function set(px: number) {
    width.value = clampColumnWidth(px);
    try { localStorage.setItem(STORAGE_KEY, String(width.value)); } catch { /* session only */ }
  }
  return { width, set, reset: () => set(COLUMN_WIDTH_LIMITS.default) };
}
