"""Energy-based voice activity detection over a stream of audio frames.

Pure logic, no I/O: feed fixed-size int16 frames, get complete utterances back.
The noise floor adapts with an exponential moving average while nobody speaks,
so the speech threshold follows the room's ambient level.
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np

DEFAULT_MIC_SENSITIVITY = 50
MIN_MIC_SENSITIVITY, MAX_MIC_SENSITIVITY = 0, 100


def sensitivity_scale(sensitivity: int) -> float:
    """Map the user's 0-100 mic sensitivity onto a speech-threshold scale.

    50 is exactly today's default (scale 1.0). Exponential, so steps feel
    even in both directions: 0 doubles the threshold (a noisy room must
    shout to trip the mic), 100 halves it (quiet rooms, soft speakers).
    The scale never drops the effective multiplier below the noise floor,
    so a maxed slider cannot leave the mic permanently open.
    """
    return 2.0 ** ((DEFAULT_MIC_SENSITIVITY - sensitivity) / DEFAULT_MIC_SENSITIVITY)


@dataclass(frozen=True)
class VadConfig:
    sample_rate: int = 16_000
    frame_ms: int = 30
    noise_floor_alpha: float = 0.05
    speech_multiplier: float = 3.0
    min_speech_rms: float = 300.0
    start_frames: int = 2
    end_silence_ms: int = 2000
    pre_roll_ms: int = 700
    min_utterance_ms: int = 400
    max_utterance_ms: int = 180_000
    # smart_turn may close early only after at least this much silence, so a
    # sensitive setting can't cut through a user still talking with tiny gaps.
    smart_turn_min_silence_ms: int = 400

    @property
    def frame_samples(self) -> int:
        return self.sample_rate * self.frame_ms // 1000


def _rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(frame.astype(np.float64)))))


@dataclass
class UtteranceSegmenter:
    config: VadConfig = field(default_factory=VadConfig)

    def __post_init__(self) -> None:
        pre_roll_frames = max(1, self.config.pre_roll_ms // self.config.frame_ms)
        self._pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_frames)
        self._noise_floor = self.config.min_speech_rms
        self._speech_run = 0
        self._silence_run = 0
        self._recording: list[np.ndarray] = []
        self._pre_roll_frames_included = 0
        # Live-adjustable from the dashboard; None = use the config default.
        self.end_silence_ms_override: int | None = None
        # User's mic sensitivity (0-100); None = DEFAULT_MIC_SENSITIVITY.
        self.mic_sensitivity_override: int | None = None
        # "soft": smart_turn may close after a short pause (fast, may over-split).
        # "hard": smart_turn may not close before end_silence — pause-split rules.
        self.smart_turn_mode = "soft"
        # Set by an external end-of-turn signal (smart_turn) to close now.
        self._close_requested = False

    def request_close(self) -> None:
        """Force the utterance in progress to close on the next frame."""
        self._close_requested = True

    def discard(self) -> bool:
        """Scratch the utterance in progress: drop its audio, deliver
        nothing. The user's 'forget what I just said' - any mode. Returns
        whether something was actually discarded."""
        if not self.is_recording:
            return False
        self._recording = []
        self._close_requested = False
        return True

    def flush(self) -> np.ndarray | None:
        """Close the utterance in progress RIGHT NOW and return its audio.

        For hard end-of-turn signals that outrank silence detection — the
        user hitting mic mute, a device teardown. Unlike request_close this
        needs no further frame: with a muted mic no frame will ever come.
        Returns None when nothing was recording or the clip is too short.
        """
        if not self.is_recording:
            return None
        self._close_requested = False
        return self._finish_utterance()

    @property
    def _end_silence_ms(self) -> int:
        return self.end_silence_ms_override or self.config.end_silence_ms

    @property
    def is_recording(self) -> bool:
        return bool(self._recording)

    @property
    def recording_frames(self) -> list[np.ndarray]:
        """Frames captured so far in the utterance in progress (incl. pre-roll)."""
        return list(self._recording)

    def feed(self, frame: np.ndarray) -> np.ndarray | None:
        """Consume one frame; return a full utterance when one just ended."""
        loud = self._is_speech(_rms(frame))
        if self.is_recording:
            return self._feed_recording(frame, loud)
        return self._feed_idle(frame, loud)

    def _is_speech(self, rms: float) -> bool:
        sensitivity = (
            self.mic_sensitivity_override
            if self.mic_sensitivity_override is not None
            else DEFAULT_MIC_SENSITIVITY
        )
        threshold = sensitivity_scale(sensitivity) * max(
            self.config.min_speech_rms,
            self._noise_floor * self.config.speech_multiplier,
        )
        return rms >= threshold

    def _feed_idle(self, frame: np.ndarray, loud: bool) -> None:
        self._pre_roll.append(frame)
        if loud:
            self._speech_run += 1
            if self._speech_run >= self.config.start_frames:
                self._recording = list(self._pre_roll)
                self._pre_roll_frames_included = len(self._pre_roll) - self._speech_run
                self._silence_run = 0
        else:
            self._speech_run = 0
            alpha = self.config.noise_floor_alpha
            self._noise_floor = (1 - alpha) * self._noise_floor + alpha * _rms(frame)
        return None

    def _feed_recording(self, frame: np.ndarray, loud: bool) -> np.ndarray | None:
        self._recording.append(frame)
        self._silence_run = 0 if loud else self._silence_run + 1

        silence_ms = self._silence_run * self.config.frame_ms
        ended_by_silence = silence_ms >= self._end_silence_ms
        too_long = (
            len(self._recording) * self.config.frame_ms >= self.config.max_utterance_ms
        )
        # smart_turn (close_requested) may end the utterance early — but only
        # after a real pause, never while the user is still talking through
        # micro-gaps. In "hard" mode pause-split fully rules: smart_turn cannot
        # close before end_silence_ms, so a high pause-split never over-splits.
        gate_ms = (
            self._end_silence_ms
            if self.smart_turn_mode == "hard"
            else self.config.smart_turn_min_silence_ms
        )
        smart_close = self._close_requested and silence_ms >= gate_ms
        if not (ended_by_silence or too_long or smart_close):
            return None
        self._close_requested = False
        return self._finish_utterance()

    def _finish_utterance(self) -> np.ndarray | None:
        utterance = np.concatenate(self._recording)
        self._recording = []
        self._speech_run = 0
        self._pre_roll.clear()

        speech_frames = (
            len(utterance) // self.config.frame_samples
            - self._pre_roll_frames_included
            - self._silence_run
        )
        speech_ms = speech_frames * self.config.frame_ms
        self._silence_run = 0
        self._pre_roll_frames_included = 0
        if speech_ms < self.config.min_utterance_ms:
            return None
        return utterance
