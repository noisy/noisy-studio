/** Typed client for the listener daemon — the app's only fetch site.
 *
 * All URLs are relative: same-origin when the daemon serves the built app
 * at /next, proxied by Vite in development (see vite.config.ts).
 */

import type { Character, DaemonStatus, InputDevice, SettingsPatch, Utterance, HotkeyState } from "../types";
import { canonicalCharacter } from "../character";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`GET ${path} → HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

async function post(path: string, body: object): Promise<void> {
  const response = await fetch(path, { method: "POST", body: JSON.stringify(body) });
  if (!response.ok) throw new Error(`POST ${path} → HTTP ${response.status}`);
}

async function postJson<T>(path: string, body: object): Promise<T> {
  const response = await fetch(path, { method: "POST", body: JSON.stringify(body) });
  if (!response.ok) throw new Error(`POST ${path} → HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export function getStatus(): Promise<DaemonStatus> {
  return getJson<DaemonStatus>("/status");
}

export interface DaemonEvent {
  seq: number;
  ts: number;
  kind: string;
  detail: string;
}

export async function getEvents(sinceSeq: number): Promise<DaemonEvent[]> {
  const body = await getJson<{ events: DaemonEvent[] }>(`/events?since=${sinceSeq}`);
  return body.events;
}

export async function getUtterances(agent?: string): Promise<Utterance[]> {
  const query = agent ? `?agent=${encodeURIComponent(agent)}` : "";
  const body = await getJson<{ utterances: Utterance[] }>(`/utterances${query}`);
  return body.utterances;
}

export async function getCharacter(agent?: string): Promise<Character> {
  const query = agent ? `?agent=${encodeURIComponent(agent)}` : "";
  const body = await getJson<{ character: Character }>(`/character${query}`);
  return canonicalCharacter(body.character);
}

export function setMuted(muted: boolean): Promise<void> {
  return post("/mute", { muted });
}

/** Speaker-side mute: Claude's speech parks silently as UNHEARD cards. */
export function setVoiceMuted(muted: boolean): Promise<void> {
  return post("/voice-mute", { muted });
}

/** One xAI call site's live verdict — rendered separately from the rest,
 * so a flaky voice endpoint can't masquerade as a bad key. */
export interface EndpointCheck {
  ok?: boolean;
  ms?: number;
  detail?: string;
  /** Still running — the daemon reports verdicts as they land. */
  pending?: boolean;
}
export type DiagnosticChecks = Record<string, EndpointCheck>;

/** Verify-then-commit: live-checks every xAI call site with the candidate
 * key. A key failing its own check is rejected server-side (ok: false) —
 * the checks come back either way so the form can show WHY. */
export async function saveApiKey(
  key: string,
): Promise<{ ok: boolean; checks?: DiagnosticChecks; error?: string }> {
  const response = await fetch("/credentials", {
    method: "POST",
    body: JSON.stringify({ xai_api_key: key }),
  });
  const body = await response.json().catch(() => ({}));
  return { ok: response.ok, ...body };
}

/** The same per-endpoint checks, on demand (SETTINGS → RUN CHECKS). */
export async function runDiagnostics(): Promise<DiagnosticChecks> {
  const body = await getJson<{ checks: DiagnosticChecks }>("/diagnose");
  return body.checks;
}

export function setMode(mode: "batch" | "live"): Promise<void> {
  return post("/mode", { mode });
}

export function setSettings(patch: SettingsPatch): Promise<void> {
  return post("/settings", patch);
}

export async function getDevices(): Promise<InputDevice[]> {
  const body = await getJson<{ devices: InputDevice[] }>("/devices");
  return body.devices;
}

/** Returns the agent the daemon ACTUALLY made active, which is not always
 *  the one asked for - the caller must reconcile against it rather than
 *  assume the request won. */
export async function setActiveAgent(name: string): Promise<string | null> {
  const body = await postJson<{ active_agent: string | null }>(
    "/active-agent", { name },
  );
  return body.active_agent ?? null;
}

export function dismissAgent(name: string): Promise<void> {
  return post("/dismiss-agent", { name });
}

export function reorderAgents(order: string[]): Promise<void> {
  return post("/reorder-agents", { order });
}

export function setAgentMuted(agent: string, muted: boolean): Promise<void> {
  return post("/mute-agent", { agent, muted });
}

export function setCharacter(patch: Partial<Character> & { agent?: string }): Promise<void> {
  return post("/character", patch);
}

/** Renew (held=true) or release (held=false) the push-to-talk lease. */
export function setPtt(held: boolean): Promise<void> {
  return post("/ptt", { held });
}

/** Transport pause for SYSTEM-speaker playback: freezes the daemon's
 * player in place (SIGSTOP) and reports the new state. Tab playback
 * pauses client-side in useBrowserAudio instead. */
export function togglePlaybackPause(): Promise<{ paused: boolean }> {
  return postJson<{ paused: boolean }>("/playback-pause", {});
}

/** Graceful shutdown (#35): schedule (default 5 min), or 0 = right now. */
export function scheduleShutdown(delaySeconds = 300): Promise<{ shutdown_at: number }> {
  return postJson<{ shutdown_at: number }>("/shutdown", { delay_seconds: delaySeconds });
}

export function postponeShutdown(seconds = 60): Promise<void> {
  return post("/shutdown-postpone", { seconds });
}

export function cancelShutdown(): Promise<void> {
  return post("/shutdown-cancel", {});
}

/** Skip the rest of whatever is on the speakers; queued speech continues. */
export function interruptPlayback(): Promise<void> {
  return post("/interrupt", {});
}

/** Skip-all: settle every parked UNHEARD card of the conversation without
 * playing it. Returns how many cards were dismissed. */
export function skipUnheard(agent?: string): Promise<{ skipped: number }> {
  return postJson<{ skipped: number }>("/skip-unheard", agent ? { agent } : {});
}

/** Recall a transcript that still waits in the queue (AWAITING CLAUDE). */
export function cancelTranscript(utteranceId: number): Promise<void> {
  return post("/cancel", { utterance_id: utteranceId });
}

/** Replay a spoken message: no new card in the log, the user's click
 * outranks whatever is playing, and source_id ties the playback back to
 * the original bubble (so it can offer STOP while playing). */
export function speakText(
  text: string,
  sourceId: number,
  agent?: string,
  options?: { interrupt?: boolean },
): Promise<void> {
  return post("/speak", {
    text,
    wait: false,
    card: false,
    // A single replay outranks whatever is playing; batch replays
    // (catch-up) must NOT — interrupting would scramble their order.
    interrupt: options?.interrupt ?? true,
    source_id: sourceId,
    ...(agent ? { agent } : {}),
  });
}

/** Stop whatever is on the speakers; queued speech continues on its own. */
export function stopPlayback(): Promise<void> {
  return post("/interrupt", {});
}

/** Voice-provider switching (issues #36/#37): the catalog describes every
 * engine's setup needs as data, so a new provider never means new UI code. */
export interface ProviderField {
  key: string;
  kind: "secret" | "choice" | "text";
  label: string;
  required: boolean;
  hint?: string;
  options?: string[];
  value?: string;
}

export interface ProviderEntry {
  name: string;
  kind: "cloud-api" | "local";
  label: string;
  directions: ("tts" | "stt")[];
  streaming: { tts: boolean; stt: boolean };
  ready: boolean;
  /** When not ready: why, and how to fix it (rendered inline). */
  ready_detail?: string;
  fields: ProviderField[];
}

export interface ModelDownload {
  name: string;
  label: string;
  state: "missing" | "downloading" | "done" | "error";
  done_bytes: number;
  total_bytes: number;
  detail: string;
}

export interface ProvidersInfo {
  catalog: ProviderEntry[];
  active: { tts: string; stt: string };
  downloads?: ModelDownload[];
}

export function getProviders(): Promise<ProvidersInfo> {
  return getJson<ProvidersInfo>("/providers");
}

/** Switch engines and/or store provider options — active immediately,
 * the daemon re-reads the selection on every call. */
export function setProviders(patch: {
  tts?: string;
  stt?: string;
  local?: Record<string, string>;
  /** Re-kick the model downloads (the RETRY after a failed fetch). */
  prefetch?: boolean;
}): Promise<{ tts: string; stt: string }> {
  return postJson<{ tts: string; stt: string }>("/providers", patch);
}

/** Ask macOS for Input Monitoring now (the settings GRANT button, #97). */
export function requestHotkeyPermission(): Promise<HotkeyState> {
  return postJson<HotkeyState>("/hotkeys/permission", {});
}

export interface SpeechEngine {
  id: string; provider: string; direction: 'stt' | 'tts'; label: string;
  location: string; model: string; live: boolean; description: string; languages: string;
  state: 'ready' | 'setup' | 'download' | 'downloading' | 'error' | 'unsupported'; detail: string;
  setup_action?: 'system-settings';
  voices: {id: string; label: string}[]; bindings: Record<string, string>;
}
export interface SpeechSettingsInfo {
  revision: string; active: {stt: string; tts: string}; current_voice_labels?: Record<string, string>; engines: SpeechEngine[]; downloads: ModelDownload[];
}
export interface SpeechSettingsPatch {
  operation: 'prepare' | 'apply'; choice: string; revision: string; bindings: Record<string, string>;
}
async function speechRequest<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(path, body === undefined ? undefined : {method:'POST', body:JSON.stringify(body)});
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw Object.assign(new Error(typeof payload?.error === 'string' ? payload.error : 'Could not reach speech settings. Check the connection and retry.'), {recovery:payload?.recovery});
  return payload as T;
}
export function getSpeechSettings(): Promise<SpeechSettingsInfo> { return speechRequest('/speech-settings'); }
export function updateSpeechSettings(patch: SpeechSettingsPatch): Promise<SpeechSettingsInfo> { return speechRequest('/speech-settings', patch); }
export function previewSpeechVoice(choice: string, voice: string): Promise<{audio: string; content_type: string}> {
  return speechRequest('/speech-settings/preview', {choice, voice});
}
export function previewRecognition(choice: string, audio: string): Promise<{text: string; elapsed_ms: number}> {
  return speechRequest('/speech-settings/transcribe', {choice, audio});
}

export function restoreSpeechSettings(revision: string): Promise<SpeechSettingsInfo> {
  return speechRequest('/speech-settings', {operation:'restore-backup', revision});
}
