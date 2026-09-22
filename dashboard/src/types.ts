/** Shapes of the listener daemon's HTTP API responses. */

export type HotkeyAction = "hold" | "toggle" | "scratch" | "tab1" | "tab2" | "tab3" | "tab4";
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
}

export interface DaemonStatus {
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
    { label: string; online: boolean; activated_at: number; offline_since: number | null; manual_pos?: number | null }
  >;
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
