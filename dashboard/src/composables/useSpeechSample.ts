import { onUnmounted, ref } from 'vue';

/** A bounded sample from the daemon's native microphone, never the renderer. */
export function useSpeechSample(onSample: (wav: string) => Promise<void>) {
  const recording = ref(false);
  const error = ref('');
  let identifier = '';
  let generation = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  async function request(action: string, id = '') {
    const response = await fetch('/speech-settings/sample', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action, id}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not record from the native microphone.');
    return data;
  }
  function cancel() {
    generation++; clearTimeout(timer); recording.value = false;
    const id = identifier; identifier = '';
    return id ? request('cancel', id).catch(() => {}) : Promise.resolve();
  }
  async function start() {
    const cancelled = cancel(); error.value = ''; const current = generation;
    await cancelled;
    if (current !== generation) return;
    const result = await request('start');
    if (current !== generation) { void request('cancel', result.id).catch(() => {}); return; }
    identifier = result.id; recording.value = true;
    timer = setTimeout(() => { void finish(); }, 15000);
  }
  async function finish() {
    const id = identifier; if (!id) return;
    const current = generation;
    identifier = ''; recording.value = false; clearTimeout(timer);
    try {
      const result = await request('finish', id);
      if (current === generation) await onSample(result.audio);
    } catch (cause) {
      if (current === generation) error.value = cause instanceof Error ? cause.message : 'Native microphone recording failed.';
    }
  }
  onUnmounted(cancel);
  return {recording, error, start, finish, cancel};
}
