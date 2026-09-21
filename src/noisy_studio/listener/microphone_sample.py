"""Bounded native microphone samples isolated from agent conversations."""
import base64
import io
import threading
import time
import uuid
import wave

SAMPLE_SECONDS = 15


class MicrophoneSample:
    def __init__(self, sample_rate=16000, clock=time.monotonic):
        self.sample_rate = sample_rate
        self.clock = clock
        self._lock = threading.Lock()
        self._id = None
        self._audio = bytearray()
        self._until = 0.0

    def start(self):
        with self._lock:
            if self._id and self.clock() < self._until:
                raise ValueError('A microphone sample is already being recorded.')
            self._id = uuid.uuid4().hex
            self._audio.clear()
            self._until = self.clock() + SAMPLE_SECONDS
            return self._id

    def feed(self, pcm: bytes):
        with self._lock:
            if not self._id or self.clock() >= self._until:
                return
            remaining = self.sample_rate * SAMPLE_SECONDS * 2 - len(self._audio)
            self._audio.extend(pcm[:remaining])

    def finish(self, identifier, cancel=False):
        with self._lock:
            if not self._id or identifier != self._id:
                raise ValueError('This microphone sample is no longer active.')
            audio = bytes(self._audio)
            self._id = None
            self._audio.clear()
        if cancel:
            return ''
        if not audio:
            raise ValueError('No microphone audio arrived. Connect a microphone and check system permissions.')
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio)
        return base64.b64encode(output.getvalue()).decode('ascii')
