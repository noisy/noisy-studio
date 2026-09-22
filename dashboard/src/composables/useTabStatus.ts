/** Tab honesty (#30): the browser tab as a status surface.
 *
 * Title says who has the voice right now; the favicon is a canvas-drawn
 * state glyph - no asset files, updated in place:
 *   🔇 muted · 🗣 agent speaking · 🎙 armed/recording · ⏸ idle
 * Works while the window is unfocused - that is the whole point.
 */

import { watch, type Ref } from "vue";
import type { DaemonStatus } from "../types";
import { conversationLabel } from "../conversationLabel";

function drawFavicon(glyph: string): void {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.font = "56px serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, 32, 36);
  let link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    document.head.append(link);
  }
  link.href = canvas.toDataURL("image/png");
}

export function useTabStatus(status: Ref<DaemonStatus | null>): void {
  watch(
    () => {
      const s = status.value;
      if (!s) return "⏸|Noisy Studio";
      const speaking = (s.speaking_agents ?? [])[0] ?? "";
      const labelFor = (key: string) => conversationLabel(
        s.agents_meta?.[key]?.label || s.agent_labels?.[key], key,
      );
      const active = s.active_agent ? labelFor(s.active_agent) : "Noisy Studio";
      if (s.muted) return `🔇|muted — ${active || "Noisy Studio"}`;
      if (speaking || s.claude_speaking) return `🗣|▶ ${speaking ? labelFor(speaking) : active} — Noisy Studio`;
      if (s.recording) return `🎙|● recording — ${active}`;
      if (s.listening) return `🎙|${active} — Noisy Studio`;
      return `⏸|${active} — Noisy Studio`;
    },
    (packed) => {
      const [glyph, title] = packed.split("|");
      document.title = title;
      drawFavicon(glyph);
    },
    { immediate: true },
  );
}
