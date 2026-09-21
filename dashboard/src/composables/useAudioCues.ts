/** Subtle audio cues on conversation events, with localStorage-backed
 * preferences (they are a per-browser matter, not daemon state). */

import { computed, ref, watch, type Ref } from "vue";
import type { DaemonStatus, Utterance } from "../types";
import { detectCues, snapshotUtterances, type CueName } from "./cueEvents";
import { HUM_DEFAULT_VOLUME, playCue, startRecordingHum, stopRecordingHum, type HumNoise } from "./cueSounds";

const STORAGE_KEY = "noisy-studio.audio-cues";

export interface CuePrefs {
  enabled: boolean;
  cues: Record<CueName, boolean>;
  /** Barely-audible drone while the mic is capturing (all modes). */
  recordingHum?: boolean;
  humNoise?: HumNoise;
  humVolume?: number; // 0..1
}

export const CUE_LABELS: Record<CueName, string> = {
  committed: "YOUR MESSAGE TRANSCRIBED",
  delivered: "DELIVERED TO CLAUDE",
  claude: "CLAUDE'S MESSAGE ARRIVED",
  unheard: "PARKED WHILE MUTED",
  error: "SYSTEM ERROR",
};

function defaultPrefs(): CuePrefs {
  return {
    enabled: true, // on by default — the cues carry real state changes
    // "claude" defaults OFF: the message announces itself by SPEAKING -
    // a blip on top is redundant (muted arrivals have their own cue).
    cues: { committed: true, delivered: true, claude: false, unheard: true, error: true },
    recordingHum: true,
    humNoise: "pink" as HumNoise,
    humVolume: HUM_DEFAULT_VOLUME,
  };
}

function loadPrefs(): CuePrefs {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "");
    return { ...defaultPrefs(), ...stored, cues: { ...defaultPrefs().cues, ...stored.cues } };
  } catch {
    return defaultPrefs();
  }
}

export function useAudioCues(
  utterances: Ref<Utterance[]>,
  status: Ref<DaemonStatus | null>,
  errorCount: Ref<number>,
  /** utterancesFor from useDaemonState - the agent the list was filtered
   * for, set atomically with it. */
  viewedAgent?: Ref<string | null>,
) {
  const prefs = ref<CuePrefs>(loadPrefs());
  watch(
    prefs,
    (value) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
      } catch {
        // storage may be unavailable — cues just won't persist
      }
    },
    { deep: true },
  );

  function play(cue: CueName) {
    if (prefs.value.enabled && prefs.value.cues[cue]) playCue(cue);
  }

  let previous = snapshotUtterances([]);
  // Tab switches are silent (#33): a view change is the USER navigating,
  // not conversation events - reset the baseline without emitting cues.
  // KEY SUBTLETY (the bug's third life): the marker must be the agent the
  // LIST WAS FILTERED FOR (utterancesFor), not the currently viewed agent -
  // viewedAgent flips instantly on click while an in-flight poll still
  // delivers the OLD tab's list, which used to poison the baseline and
  // make the NEXT poll read as fresh messages. System rows shared by every
  // tab defeat the id-swap fallback, so this marker is the real guard.
  let previousAgent = viewedAgent?.value ?? null;
  watch(utterances, (list) => {
    const agent = viewedAgent?.value ?? null;
    const viewChanged = agent !== previousAgent;
    previousAgent = agent;
    if (viewChanged) {
      previous = snapshotUtterances(list);
      return;
    }
    const cues = detectCues(previous, list, status.value?.voice_muted ?? false);
    previous = snapshotUtterances(list);
    cues.forEach(play);
  });

  watch(errorCount, (next, before) => {
    if (next > before) play("error");
  });

  // The hum means "the system can hear you", not "you are talking": in
  // push-to-talk (hold or toggle) it starts the moment the lease opens,
  // before any word is spoken; in auto mode arming and recording coincide,
  // so it tracks the recording flag there. Muted always wins.
  const micArmed = () => {
    const s = status.value;
    if (!s || s.muted) return false;
    if (s.detection_mode === "ptt") return s.ptt_held || s.recording;
    return s.recording;
  };
  const humActive = () =>
    micArmed() && prefs.value.enabled && (prefs.value.recordingHum ?? true);
  watch(
    // Restart with fresh params when the noise color or volume changes
    // while armed - startRecordingHum replaces a running hum in place.
    () => (humActive() ? `${prefs.value.humNoise ?? "pink"}|${prefs.value.humVolume ?? HUM_DEFAULT_VOLUME}` : ""),
    (key) => {
      if (!key) return stopRecordingHum();
      startRecordingHum(prefs.value.humNoise ?? "pink", prefs.value.humVolume ?? HUM_DEFAULT_VOLUME);
    },
  );

  const enabled = computed({
    get: () => prefs.value.enabled,
    set: (value: boolean) => {
      prefs.value.enabled = value;
      if (value) playCue("delivered"); // audible confirmation + unlocks WebAudio
    },
  });

  return { prefs, enabled };
}
