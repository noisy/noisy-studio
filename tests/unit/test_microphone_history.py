from noisy_studio.listener.microphone_history import MicrophoneHistory
from noisy_studio.listener.state import ListenerState


def rows(state):
    return [(u['text'], u['detail']) for u in state.utterances() if u['role'] == 'system']


def test_retries_and_reopens_are_silent_until_the_effective_microphone_changes():
    state = ListenerState()
    now = [0.0]
    history = MicrophoneHistory(state, clock=lambda: now[0])
    for effective, opened in [('Headset', 'Headset'), ('Headset', 'Headset'),
                              ('Built-in', ''), ('Built-in', ''), ('Built-in', ''),
                              ('Headset', 'Headset')]:
        history.record(effective, opened, 'Headset')
        now[0] += 10
    assert rows(state) == [
        ('MIC → Headset', ''),
        ("MIC → system default (waiting for 'Headset')", ''),
        ('MIC → Headset', ''),
    ]


def test_restart_with_same_microphone_is_silent_but_a_different_one_is_reported(tmp_path):
    path = tmp_path / 'microphone-state.json'
    MicrophoneHistory(ListenerState(), path).record('Headset', 'Headset', 'Headset')
    state = ListenerState()
    history = MicrophoneHistory(state, path)
    history.record('Headset', 'Headset', 'Headset')
    history.record('Desk mic', 'Desk mic', 'Desk mic')
    assert rows(state) == [('MIC → Desk mic', '')]


def test_brief_flapping_compacts_repeated_transition_at_its_latest_time():
    state = ListenerState()
    now = [100.0]
    history = MicrophoneHistory(state, clock=lambda: now[0])
    history.record('Headset', 'Headset', 'Headset')
    now[0] = 101
    history.record('Built-in', '', 'Headset')
    now[0] = 102
    history.record('Headset', 'Headset', 'Headset')
    assert rows(state) == [('MIC → Headset', '×2'), ("MIC → system default (waiting for 'Headset')", '')]
    assert state.utterances()[0]['started_at'] == 102


def test_invalid_saved_device_does_not_prevent_reporting(tmp_path):
    path = tmp_path / 'microphone-state.json'
    path.write_text('broken')
    state = ListenerState()
    MicrophoneHistory(state, path).record('Headset', 'Headset', 'Headset')
    assert rows(state) == [('MIC → Headset', '')]
