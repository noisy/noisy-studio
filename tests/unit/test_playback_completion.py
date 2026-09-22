from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import asyncio

import pytest

from noisy_studio import playback, tts_stream
from noisy_studio.listener import speech
from noisy_studio.listener.daemon import _ptt_barge_in
from noisy_studio.listener.state import ListenerState
from noisy_studio.providers.base import SynthesizedAudio


@pytest.fixture
def completion_case(monkeypatch):
    state = ListenerState()
    state.register_agent('a1')
    state.set_active_agent('a1')
    clip = state.create_utterance('claude', 'queued', text='complete reply', agent='a1')
    monkeypatch.setattr(speech, '_hold_for_user_turn', lambda *args: None)
    monkeypatch.setattr(speech, 'ECHO_TAIL_SECONDS', 0)
    return state, clip


def run_prepared(state, clip, stream=False):
    future = Future()
    future.set_result(speech._PreparedSpeech(
        'orion', 'en', 1.0, stream=stream,
        audio=None if stream else SynthesizedAudio(b'audio', 'audio/mpeg', 1.0),
    ))
    return speech._play_prepared(state, 'complete reply', 'a1', clip, clip, future)


def card_status(state, clip):
    return next(u['status'] for u in state.utterances() if u['id'] == clip)


def test_ptt_during_echo_guard_keeps_completed_batch_reply_played(monkeypatch, completion_case):
    state, clip = completion_case
    monkeypatch.setattr(speech, '_play_audio', AsyncMock())
    observed = []

    def echo_guard(_seconds):
        observed.append((_ptt_barge_in(state), card_status(state, clip)))

    monkeypatch.setattr(speech.time, 'sleep', echo_guard)
    run_prepared(state, clip)

    assert observed == [(False, 'played')]
    assert card_status(state, clip) == 'played'


@pytest.mark.parametrize('cleanup_failure', [False, True])
def test_stream_completion_releases_card_and_mic_before_cleanup(monkeypatch, completion_case, cleanup_failure):
    state, clip = completion_case
    observed = []

    async def stream(*args):
        args[-1]()
        observed.append((state.playing_clip(), state.paused, _ptt_barge_in(state)))
        if cleanup_failure:
            raise OSError('connection cleanup failed after playback')

    monkeypatch.setattr(speech, '_stream_and_play', stream)
    run_prepared(state, clip, stream=True)

    assert observed == [(None, False, False)]
    assert card_status(state, clip) == 'played'


@pytest.mark.parametrize('label', ['unheard', 'skipped'])
def test_completion_does_not_overwrite_an_earlier_interruption(monkeypatch, completion_case, label):
    state, clip = completion_case

    async def stream(*args):
        state.interrupt_playing_as_unheard('user action', label=label)
        args[-1]()

    monkeypatch.setattr(speech, '_stream_and_play', stream)
    run_prepared(state, clip, stream=True)

    assert card_status(state, clip) == f'{label} — user action'


@pytest.mark.parametrize('buffered', [False, True])
@pytest.mark.parametrize('returncode', [0, -9, 1])
async def test_stream_player_reports_only_successful_completion(monkeypatch, buffered, returncode):
    process = SimpleNamespace(
        returncode=returncode, wait=AsyncMock(),
        stdin=SimpleNamespace(write=Mock(), drain=AsyncMock(), close=Mock()),
    )
    monkeypatch.setattr(tts_stream, '_stream_player_command', lambda: None if buffered else ['player'])
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', AsyncMock(return_value=process))
    registered = []
    monkeypatch.setattr(playback, 'register_player', lambda p: registered.append('start'))
    monkeypatch.setattr(playback, 'unregister_player', lambda p: registered.append('end'))
    callback = Mock()
    queue = asyncio.Queue()
    queue.put_nowait(None)

    if returncode > 0:
        with pytest.raises(playback.PlaybackError):
            await tts_stream._play_from_stream(queue, callback)
    else:
        await tts_stream._play_from_stream(queue, callback)

    assert (registered, callback.call_count) == (['start', 'end'], int(returncode == 0))
