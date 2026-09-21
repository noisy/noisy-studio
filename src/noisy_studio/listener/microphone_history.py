"""Report effective microphone changes, independently of stream reopen attempts."""
import json
import time
from pathlib import Path

COMPACT_WINDOW_SECONDS = 5.0


class MicrophoneHistory:
    def __init__(self, state, path: Path | None = None, clock=time.time):
        self.state = state
        self.path = path
        self.clock = clock
        self.last_device = None
        self.recent = {}
        if path:
            try:
                saved = json.loads(path.read_text())
                if isinstance(saved, dict) and isinstance(saved.get('device'), str):
                    self.last_device = saved['device']
            except (OSError, ValueError):
                pass

    def record(self, effective: str, opened: str, wanted: str) -> None:
        if effective == self.last_device:
            return
        self.last_device = effective
        label = opened or 'system default'
        text = f'MIC → {label}'
        if wanted and wanted != opened:
            text += f" (waiting for '{wanted}')"
        now = self.clock()
        self.recent = {key: value for key, value in self.recent.items()
                       if now - value[1] <= COMPACT_WINDOW_SECONDS}
        previous = self.recent.get(text)
        if previous:
            row, first_at, count = previous
            count += 1
            # A repeated transition is a current event, including for newly
            # opened conversations. Keep its order relative to intervening changes.
            self.state.update_utterance(row, detail=f'×{count}', started_at=now, committed_at=now)
            self.recent[text] = (row, first_at, count)
        else:
            row = self.state.create_utterance('system', '', text=text)
            self.recent[text] = (row, now, 1)
        if self.path:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_suffix('.tmp')
                temporary.write_text(json.dumps({'device': effective}))
                temporary.replace(self.path)
            except OSError:
                self.state.add_event('mic_error', 'Could not save the current microphone for restart recovery')
