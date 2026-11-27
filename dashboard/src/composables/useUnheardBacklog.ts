import { computed, type Ref } from "vue";
import { setAgentMuted, setVoiceMuted, skipUnheard, speakText } from "../api/client";
import { replaySpeechText } from "../components/bubbleStatus";
import type { DaemonStatus, Utterance } from "../types";

const swallow = () => {};

/** The conversation's parked (unheard) backlog and the ways out of it.
 * Every exit fires daemon calls only; the next snapshot reflects reality. */
export function useUnheardBacklog(
  status: Ref<DaemonStatus | null>,
  utterances: Ref<Utterance[]>,
  viewedAgent: Ref<string | null>,
) {
  const unheard = computed(() =>
    utterances.value.filter((u) => u.role === "claude" && u.status.includes("unheard")),
  );

  // Every exit means "from now on I listen live": lift BOTH the global
  // voice mute and this conversation's own mute, so the next message
  // plays instead of parking and reopening the catch-up row.
  async function listenLive(agent: string | null) {
    await setVoiceMuted(false).catch(swallow);
    if (agent && (status.value?.muted_agents ?? []).includes(agent)) {
      await setAgentMuted(agent, false).catch(swallow);
    }
  }

  // Catch up: unmute FIRST (or the replays would park as unheard again),
  // then queue every parked message in arrival order; the playback queue
  // serializes them, each stoppable with its ⏹.
  async function catchUp() {
    await listenLive(viewedAgent.value);
    // Sequential awaits + interrupt:false — parallel POSTs can arrive out of
    // order and an interrupting replay would jump the queue, so a batch
    // catch-up must do neither (it played last-before-previous once).
    const parked = [...unheard.value].sort(
      (a, b) => (a.committed_at || a.started_at) - (b.committed_at || b.started_at),
    );
    for (const u of parked) {
      await speakText(replaySpeechText(u.text), u.id, undefined, { interrupt: false }).catch(swallow);
    }
  }

  // Skip-all: the mirror of catch-up — settle the parked queue unplayed in
  // one daemon call, THEN unmute (the other order could still start a card
  // that was pending when the button was clicked).
  async function skipAll() {
    const agent = viewedAgent.value;
    await skipUnheard(agent ?? undefined).catch(swallow);
    await listenLive(agent);
  }

  return { unheard, catchUp, skipAll };
}
