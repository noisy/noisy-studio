import { computed, ref, watch, type Ref } from "vue";
import { getCharacter, setCharacter } from "../api/client";
import { canonicalCharacter } from "../character";
import type { Character, DaemonStatus } from "../types";

type Patch = Partial<Character>;
type Entry = {
  confirmed: Character | null;
  edits: Patch[];
  revision: number;
  settledAt: number;
  reading: boolean;
  error: string;
};

/** One save queue per conversation; snapshots never erase a pending choice. */
export function conversationCharacter(
  selected: Ref<string | null>,
  initial: Character | null,
  cache: (value: Character) => void,
  reportError: (message: string) => void,
) {
  const character = ref<Character | null>(initial);
  const pending = ref(false);
  const error = ref("");
  const entries = new Map<string, Entry>();

  function entry(agent: string): Entry {
    if (!entries.has(agent)) entries.set(agent, {
      confirmed: null, edits: [], revision: 0, settledAt: 0, reading: false, error: "",
    });
    return entries.get(agent)!;
  }

  function render() {
    const current = selected.value ? entry(selected.value) : null;
    pending.value = !!current?.edits.length;
    error.value = current?.error ?? "";
    character.value = current?.confirmed
      ? current.edits.reduce<Character>((value, patch) => ({ ...value, ...patch }), current.confirmed)
      : null;
    if (character.value && !pending.value) cache(character.value);
  }
  watch(selected, render, { flush: "sync" });

  function apply(status: DaemonStatus, askedAt: number) {
    for (const [agent, value] of Object.entries(status.agent_characters ?? {})) {
      const current = entry(agent);
      if (current.edits.length || askedAt < current.settledAt) continue;
      current.revision++;
      current.confirmed = canonicalCharacter(value);
    }
    const agent = selected.value;
    if (agent && !status.agent_characters?.[agent]) {
      const current = entry(agent);
      const voice = status.agent_voices?.[agent];
      if (!current.edits.length && !current.reading &&
          (!current.confirmed || (voice && voice !== current.confirmed.voice))) {
        const revision = ++current.revision;
        current.reading = true;
        getCharacter(agent).then((value) => {
          if (revision === current.revision) current.confirmed = value;
        }).catch(() => {}).finally(() => { current.reading = false; render(); });
      }
    }
    render();
  }

  async function saveEdits(agent: string, current: Entry) {
    while (current.edits.length) {
      const patch = current.edits[0];
      try {
        current.confirmed = await setCharacter({ ...patch, agent });
        current.error = "";
      } catch (reason) {
        current.error = `Could not save character settings: ${(reason as Error)?.message ?? reason}`;
        reportError(current.error);
      }
      current.edits.shift();
      current.settledAt = Date.now();
      render();
    }
  }

  function change(patch: Patch) {
    const agent = selected.value;
    if (!agent) return;
    const current = entry(agent);
    if (!current.confirmed) return;
    current.revision++; // invalidate any earlier /character read
    current.error = "";
    current.edits.push(patch);
    render();
    if (current.edits.length === 1) void saveEdits(agent, current);
  }

  return { character, pending: computed(() => pending.value), error, apply, change };
}
