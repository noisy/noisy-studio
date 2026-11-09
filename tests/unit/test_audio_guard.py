import threading

import pytest

from noisy_studio.listener.audio_guard import STALL_RETRY_MAX_SECONDS, AudioCallGuard, stall_retry_seconds


def test_a_call_that_finishes_in_time_returns_its_value():
    guard = AudioCallGuard(lambda _m: None, timeout=1)
    assert guard.run('open', lambda: 42) == (True, 42)


def test_errors_reach_the_caller_so_existing_fallbacks_still_apply():
    guard = AudioCallGuard(lambda _m: None, timeout=1)
    with pytest.raises(ValueError):
        guard.run('open', lambda: (_ for _ in ()).throw(ValueError('no device')))


def test_a_stuck_call_is_abandoned_and_blocks_further_calls_until_it_returns():
    logs = []
    release = threading.Event()
    late = []
    guard = AudioCallGuard(logs.append, timeout=0.05)

    def stuck():
        release.wait(5)
        return 'stream'

    assert guard.run('closing the old input stream', stuck, on_late_result=late.append) == (False, None)
    assert guard.wedged
    ran = []
    assert guard.run('PortAudio reinit', lambda: ran.append(1)) == (False, None)
    assert ran == []  # never terminate PortAudio under a stuck call

    release.set()
    for _ in range(100):
        if late:
            break
        threading.Event().wait(0.01)
    assert late == ['stream']  # a stream opened too late is handed back to be closed
    assert guard.run('PortAudio reinit', lambda: 'ok') == (True, 'ok')
    assert any('did not return' in m for m in logs)
    assert any('finally returned' in m for m in logs)


def test_silent_reopens_back_off_instead_of_spinning():
    waits = [stall_retry_seconds(streak, base=2.0) for streak in range(8)]
    assert waits[0] == 2.0  # a fresh stall is still caught quickly
    assert waits == sorted(waits)
    assert waits[-1] == STALL_RETRY_MAX_SECONDS

