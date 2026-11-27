/** Shapes of the listener daemon's HTTP API responses. */

/** A settled conversation as the daemon lists it (/status settled_agents):
 *  hidden from the list, no longer in the agents table. */
export interface SettledAgent {
  name: string;
  label: string;
  project: string | null;
  branch: string | null;
  last_active_at: number; // epoch s
  ended: boolean;
  talk_key: string | null;
}
/** The daemon sends only the newest settled conversations, plus the total. */
export interface SettledAgents {
  total: number;
  items: SettledAgent[];
}

export type HotkeyAction = "hold" | "toggle" | "scratch" | "tab1" | "tab2" | "tab3" | "tab4" | "dictate";
export interface HotkeyProblem { kind: "collision" | "system" | "invalid"; detail: string }
export interface HotkeyState {
  configured: boolean;
  permission: "granted" | "missing" | "unavailable" | "unknown";
  armed: boolean;
  /** Chords actually armed in the tap (canonical text per action). */
  bindings?: Record<string, string>;
  /** Everything the user stored, armed or not. */
  stored?: Record<string, string>;
  problems?: Record<string, HotkeyProblem>;
  /** Conversations' own talk keys armed in the tap: {conversation key: chord}. */
  talk_keys?: Record<string, string>;
  /** Talk keys the tap could not arm: {conversation key: problem}. */
  talk_key_problems?: Record<string, HotkeyProblem>;
}

/** POST /conversation-hotkey: a conversation's own talk key, set or cleared.
 *  A refused chord (problem.kind "collision" | "invalid") leaves the old key
 *  in `talk_key`; a "system" problem is a warning and the chord is stored. */
export interface ConversationHotkeyResult {
  /** The registry key the request resolved to (an alias may be sent). */
  conversation: string;
  /** What the conversation owns now; null = no key of its own. */
  talk_key: string | null;
  /** The conversation that lost the chord to this one, if it had it. */
  moved_from: string | null;
  problem: HotkeyProblem | null;
}

/** Dictate anywhere: pasting into other apps needs macOS Accessibility. */
export interface DictationState {
  permission: "granted" | "missing" | "unavailable" | "unknown";
  /** A dictation session is recording right now. */
  active: boolean;
  /** The running (or last) session; its utterances carry the same number. */
  session?: number;
  /** Where the text cursor was when it started (global screen points). */
  anchor?: { x: number; y: number; width: number; height: number; source: "caret" | "field" | "mouse" } | null;
  /** Its words are still being recorded, transcribed or pasted. */
  pending?: boolean;
}

export interface ProviderQuota {
  provider: string;
  label: string;
  sampled_at: number | null;
  scope: 'connection' | 'unknown';
  message: string;
  windows: { label: string; used_percent: number; resets_at: number | null; stale: boolean }[];
}

export interface DaemonStatus {
  provider_usage?: ProviderQuota[];
  /** Number of older cards removed by each conversation’s retention limit. */
  history_trimmed?: Record<string, number>;
  audio_capabilities?: AudioCapabilities;
  conversations?: Record<string, { created_at?: number }>;
  /** Named speakers whose bubbles carry a palette tint (twitch purple / youtube red). */
  speaker_colors?: Record<string, string>;
  /** Free bubble titles per speaker ("YouTube · nick", "Luna - chat agent"). */
  speaker_labels?: Record<string, string>;
  listening: boolean;
  muted: boolean;
  voice_muted: boolean;
  api_key_set: boolean;
  /** A ready engine is selected both ways (local counts — no key needed). */
  voice_ready?: boolean;
  voice_labels?: Record<string, string>;
  api_key_hint: string;
  stt_latency_ms: number | null;
  tts_latency_ms: number | null;
  recording: boolean;
  claude_speaking: boolean;
  playing_utterance_id: number;
  speaking_agents: string[];
  queued: number;
  session_cost_usd: { user: number; claude: number };
  usage: { stt_seconds: number; tts_chars: number };
  credits_usd: number | null;
  recognition_live_available?: boolean;
  speech_live_available?: boolean;
  recognition_mode?: "batch" | "live" | "unavailable";
  speech_output_mode?: "batch" | "live" | "unavailable";
  mode: "batch" | "live";
  tts_mode: "batch" | "live";
  max_utterance_ms?: number;
  end_silence_ms: number;
  /** Noise gate: 0 (needs a loud voice) … 100 (hair-trigger); 50 = default. */
  mic_sensitivity: number;
  smart_turn: number;
  smart_turn_mode: "soft" | "hard";
  detection_mode: "auto" | "ptt";
  ptt_hold_key?: string;
  ptt_toggle_key?: string;
  ptt_cancel_key?: string;
  shutdown_at?: number;
  ptt_held: boolean;
  input_device: string;
  /** Global push-to-talk keys and the macOS Input Monitoring permission they need (#97). */
  hotkeys?: HotkeyState;
  dictation?: DictationState;
  /** Live per-endpoint xAI check results — partial while checks run. */
  diagnostic_checks?: Record<string, { ok?: boolean; ms?: number; detail?: string; pending?: boolean }> | null;
  activity: Record<string, { text: string; at: number }>;
  /** #16 narration-nudge silence clocks, per agent: how long it has been
   * silent, its talkative budget (null = nudging off), and whether it's
   * currently nudge-eligible (activity line fresh). */
  nudge_clocks?: Record<string, { silence: number; threshold: number | null; fresh: boolean }>;
  language: string;
  agents: Record<string, number>;
  agent_labels: Record<string, string>;
  /** Tab metadata (#11): online state + ordering keys. Absent on old daemons. */
  agents_meta?: Record<
    string,
    {
      label: string; online: boolean; activated_at: number; offline_since: number | null; manual_pos?: number | null;
      /** The tabN hotkey that reaches it; null when it has its own talk key. */
      shortcut?: number | null;
      /** Its own global talk key (canonical chord); null when it has none. */
      talk_key?: string | null;
      /** Ended, but restored from Settled: it stays in its project. */
      kept?: boolean;
    }
  >;
  /** Settled (hidden) conversations: the newest few + the total. Absent on old daemons. */
  settled_agents?: SettledAgents;
  /** Each conversation's voice, so clients can draw a portrait without
   *  fetching /character once per agent. Absent on old daemons. */
  agent_voices?: Record<string, string>;
  agent_characters?: Record<string, Character>;
  /** Waiting (undelivered) transcripts per addressee agent. */
  queued_by_agent?: Record<string, number>;
  /** Conversations whose speech parks as unheard (per-tab mute). */
  muted_agents?: string[];
  active_agent: string | null;
  /** Daemon package version, for the footer skew check. */
  version?: string;
  /** Newest published release, from the daemon's periodic GitHub check. */
  latest_version?: string | null;
}

export interface Utterance {
  delivery_state?: string;
  delivery_detail?: string;
  id: number;
  /** Human label from agent registration; absent for older daemons/history. */
  agent_label?: string;
  /** daemon = Noisy Studio speaking for itself (setup confirmations …) —
   * same voice pipeline as claude cards, but never attributed to Claude. */
  role: "user" | "claude" | "system" | "daemon";
  status: string;
  text: string;
  detail: string;
  cost_usd: number;
  agent: string | null;
  started_at: number;
  updated_at: number;
  /** When the message entered the conversation (0 = still composing). */
  committed_at: number;
  /** Real audio duration in seconds (absent for older/mid-flight cards). */
  duration_s?: number;
  /** Dictate anywhere: the session this utterance was dictated in. It
   * belongs to no conversation; its text is pasted into the focused app. */
  dictation?: number;
  /** Who inside the conversation actually said this (#22): empty/absent =
   * the main agent; a subagent's speech carries its identity here while the
   * utterance still belongs to the parent conversation's tab. */
  speaker?: string;
  /** Voice this utterance was (or will be) spoken with — drives the
   * portrait tile next to subagent bubbles. */
  voice?: string;
}

export interface Character {
  humor: number;
  honesty: number;
  verbosity: number;
  talkative: number;
  voice: string;
  speed: number;
}

export interface SettingsPatch {
  hotkeys?: Record<string, string>; // {action: chord}, "" clears (#104)
  tts_mode?: "batch" | "live";
  max_utterance_ms?: number;
  end_silence_ms?: number;
  mic_sensitivity?: number;
  smart_turn?: number;
  smart_turn_mode?: "soft" | "hard";
  detection_mode?: "auto" | "ptt";
  ptt_hold_key?: string;
  ptt_toggle_key?: string;
  ptt_cancel_key?: string;
  shutdown_at?: number;
  input_device?: string;
  language?: string;
}

export interface InputDevice {
  name: string;
  default: boolean;
  /** Device identifier when it differs from the display name. */
  value?: string;
}

/** Facts from the selected provider/model. Null codes do not mean universal support. */
export interface SpeechCapabilities {
  provider: string;
  model: string;
  modes: Array<'batch' | 'live'>;
  languages: {
    codes: string[] | null;
    auto_detect: boolean | null;
    selectable: boolean;
    exhaustive: boolean;
    purpose: 'recognition' | 'synthesis' | 'formatting' | 'voice';
    note: string;
  };
  smart_turn: {modes: Array<'live'>; minimum: number; maximum: number; off_value: number} | null;
}
export interface AudioCapabilities {
  version: 1;
  stt: SpeechCapabilities | null;
  tts: SpeechCapabilities | null;
  turn_detection: {owner: 'application'; modes: Array<'auto' | 'ptt'>};
  end_silence: {owner: 'application'; minimum_ms: number; maximum_ms: number; modes: Array<'auto'>};
}
