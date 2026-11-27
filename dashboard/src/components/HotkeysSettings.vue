<script setup lang="ts">
/* Settings > Hotkeys (#104).
 *
 * Presentational: every state comes in through props so Storybook can show
 * the tab locked (Input Monitoring missing), enabled, capturing a key, a
 * collision with one of our own actions, and a warning about a macOS
 * shortcut. Layout picked by Krzysztof on 2026-09-15: one card with push to
 * talk on the left and the per-tab keys on the right, the app-owned
 * companion keys listed below without commentary. Dictate anywhere has its
 * own card under the main one: it talks to no conversation, and it needs a
 * second permission (Accessibility, to paste), gated right there. */
import { computed } from "vue";

export interface HotkeyBinding {
  action: string;          // stable id, e.g. "hold", "toggle", "scratch", "tab1"
  label: string;           // "Hold-to-talk"
  chord: string;           // canonical, e.g. "cmd+shift+F8"; "" = unbound
  readonly?: boolean;      // Electron-owned (Ctrl+Alt+G), listed, not editable here
  problem?: { kind: "collision" | "system" | "invalid"; detail: string };
}
export interface HotkeyPane {
  title: string;
  caption?: string;        // one sentence at most; omit when the labels say it all
  bindings: HotkeyBinding[];
}

const props = withDefaults(
  defineProps<{
    permission?: "granted" | "missing" | "unavailable" | "unknown";
    /** The main card: two panes side by side. */
    talk: HotkeyPane;
    tabs: HotkeyPane;
    /** Dictate anywhere: its own card under the main one. */
    dictate?: HotkeyPane | null;
    /** macOS Accessibility, which dictation needs to paste into other apps. */
    accessibility?: "granted" | "missing" | "unavailable" | "unknown";
    /** The read-only card below (companion window keys). */
    app?: HotkeyPane | null;
    capturing?: string | null;  // action id whose field is waiting for a key
  }>(),
  { permission: "unknown", dictate: null, accessibility: "unknown", app: null, capturing: null },
);
const emit = defineEmits<{
  grant: [];
  grantAccessibility: [];
  capture: [action: string];   // user clicked a field: start listening
  clear: [action: string];
}>();

const locked = computed(() => props.permission === "missing");
// Editable cards, in order: the main one (two panes side by side), then dictation.
const cards = computed(() => [
  { key: "main", panes: [props.talk, props.tabs] },
  ...(props.dictate ? [{ key: "dictate", panes: [props.dictate] }] : []),
]);
// Only nag once a dictate key is bound: until then nothing needs to paste.
const pasteBlocked = computed(
  () => props.accessibility === "missing" && !!props.dictate?.bindings.some((b) => b.chord),
);
const GLYPH: Record<string, string> = { cmd: "⌘", shift: "⇧", alt: "⌥", ctrl: "⌃" };
const keys = (chord: string) => {
  const [base, taps] = chord.split(" ");
  const parts = base.split("+").map((k) => GLYPH[k] ?? (k.length === 1 ? k.toUpperCase() : k));
  return taps === "x2" ? [...parts, "×2"] : parts;
};
</script>

<template>
  <div class="hotkeys" :class="{ 'perm-locked': locked }">
    <div v-if="locked" class="gate" role="status">
      <div class="gatetext">
        <b>macOS is not letting Noisy Studio see your keys yet.</b>
        Global hotkeys need the Input Monitoring permission; your bindings are kept and
        arm themselves the moment it is granted. The system dialog can open behind other windows.
      </div>
      <button class="btn primary" @click="emit('grant')">Grant access</button>
    </div>
    <div v-else-if="permission === 'unavailable'" class="gate muted" role="status">
      Global hotkeys are a macOS feature.
    </div>

    <fieldset v-for="card in cards" :key="card.key" :disabled="locked" class="card" :class="card.key">
      <div v-if="card.key === 'dictate' && pasteBlocked" class="gate inset" role="status">
        <div class="gatetext">
          <b>Dictation cannot paste yet.</b>
          It puts the text into other apps through the Accessibility permission; until that is
          granted, the key records nothing. The system dialog can open behind other windows.
        </div>
        <button class="btn primary" @click="emit('grantAccessibility')">Grant access</button>
      </div>
      <section v-for="(pane, i) in card.panes" :key="pane.title" class="pane" :class="{ second: i === 1 }">
        <h3>{{ pane.title }}</h3>
        <p v-if="pane.caption" class="caption">{{ pane.caption }}</p>
        <div class="rows">
          <div v-for="b in pane.bindings" :key="b.action" class="row" :class="{ capturing: capturing === b.action, bad: b.problem && b.problem.kind !== 'system', warn: b.problem?.kind === 'system' }">
            <span class="lbl">{{ b.label }}</span>
            <button class="chord" :aria-label="`${b.label} key`" @click="emit('capture', b.action)">
              <span v-if="capturing === b.action" class="listen">Press a key, twice for a double press…</span>
              <template v-else-if="b.chord"><kbd v-for="k in keys(b.chord)" :key="k">{{ k }}</kbd></template>
              <span v-else class="unbound">Not set</span>
            </button>
            <button v-if="b.chord" class="clear" title="Clear" @click="emit('clear', b.action)">✕</button>
            <span v-else class="clear-space"></span>
            <p v-if="b.problem" class="problem">{{ b.problem.detail }}</p>
          </div>
        </div>
      </section>
    </fieldset>

    <section v-if="app" class="card">
      <h3>{{ app.title }}</h3>
      <div class="rows">
        <div v-for="b in app.bindings" :key="b.action" class="row ro">
          <span class="lbl">{{ b.label }}</span>
          <span class="chord static"><kbd v-for="k in keys(b.chord)" :key="k">{{ k }}</kbd></span>
          <span class="clear-space"></span>
        </div>
      </div>
    </section>

    <p class="foot">Click a field and press the keys you want; twice for a double press. Click elsewhere to cancel, Delete clears. macOS keeps Control with F1–F8 for itself; clashes with other apps cannot be detected. The global listener only matches the keys you bind here; nothing you type is recorded or sent anywhere.</p>
  </div>
</template>

<style scoped>
.hotkeys { display: grid; gap: 18px; min-width: 0; max-width: 760px; font-family: var(--sans); }
.gate { display: flex; align-items: center; gap: 16px; padding: 12px 14px; border: 1px solid var(--amber-dim); border-left-width: 3px; border-radius: 6px; background: var(--bg1); font-size: 12px; line-height: 1.5; color: var(--ink); }
.gate.muted { border-color: var(--line); color: var(--muted); }
.gate.inset { margin-bottom: 12px; }
.gatetext { flex: 1; min-width: 0; }
.gate b { color: var(--amber); font-weight: 400; }
.btn { font-family: var(--sans); font-size: 11px; color: var(--cyan); background: rgba(158,188,245,.06); border: 1px solid var(--line-strong); padding: 7px 14px; cursor: pointer; border-radius: 8px; flex: none; }
.btn:hover { color: var(--cyan-hi); }
/* The one live control on a locked tab must not look like part of the
   greyed block: filled, high contrast, hover lift. */
.btn.primary { color: var(--bg0); background: var(--amber); border-color: var(--amber); font-weight: 600; padding: 8px 16px; }
.btn.primary:hover { color: var(--bg0); background: var(--accent-hover, var(--amber)); }

.card { margin: 0; min-width: 0; padding: 14px 16px 16px; border: 1px solid var(--line); border-radius: 10px; background: color-mix(in srgb, var(--bg1) 60%, transparent); }
/* Not ".locked": the dashboard has a GLOBAL .locked rule that dims and
   blocks clicks on the whole element - it swallowed the GRANT button. */
.perm-locked .card { opacity: .45; pointer-events: none; }
/* two panes of EXACTLY the same width: symmetric padding, divider on the second */
.main { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.pane { min-width: 0; padding-right: 20px; }
.pane.second { padding: 0 0 0 20px; border-left: 1px dashed var(--line); }
h3 { margin: 0; font-size: 12px; font-weight: 600; letter-spacing: .02em; color: var(--ink); }
.caption { margin: 4px 0 0; font-size: 12px; line-height: 1.55; color: var(--muted); }
.rows { display: grid; gap: 8px; margin-top: 12px; }
.row { display: grid; grid-template-columns: 84px minmax(0, 1fr) 22px; align-items: center; column-gap: 8px; }
.lbl { font-size: 11px; color: var(--muted); }
.chord { display: flex; align-items: center; gap: 6px; min-height: 30px; padding: 4px 10px; border-radius: 6px; background: var(--bg1); border: 1px solid var(--line-strong); color: var(--ink); font-family: var(--sans); font-size: 12px; text-align: left; cursor: pointer; min-width: 0; }
.chord:hover { border-color: var(--cyan-dim); }
.chord.static { cursor: default; border-color: var(--line); }
kbd { font-family: var(--mono); font-size: 11px; padding: 2px 7px; border-radius: 4px; background: var(--bg0); border: 1px solid var(--line); border-bottom-width: 2px; color: var(--ink); }
.unbound { color: var(--muted); }
.listen { color: var(--cyan); }
.capturing .chord { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(158,188,245,.15); animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 50% { box-shadow: 0 0 0 5px rgba(158,188,245,.05); } }
.clear { background: none; border: 0; color: var(--muted); cursor: pointer; font-size: 12px; padding: 4px 0; width: 22px; }
.clear:hover { color: var(--ink); }
.clear-space { width: 22px; }
.problem { grid-column: 2 / span 2; margin: 2px 0 0; font-size: 11px; line-height: 1.5; }
.bad .chord { border-color: #d98a8a; }
.bad .problem { color: #e3a3a3; }
.warn .chord { border-color: var(--amber-dim); }
.warn .problem { color: var(--amber); }
.foot { margin: 0; font-size: 12px; line-height: 1.6; color: var(--muted); }

@container (max-width: 560px) {
  .main { grid-template-columns: minmax(0, 1fr); }
  .pane { padding-right: 0; }
  .pane.second { padding: 14px 0 0; margin-top: 14px; border-left: 0; border-top: 1px dashed var(--line); }
}
</style>
