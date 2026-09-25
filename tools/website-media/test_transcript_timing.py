import pytest

from transcript_timing import align_activities, with_streaming_transcripts


@pytest.mark.parametrize('final_ms, expected_end', [(12712, 12712), (14500, 13682)])
def test_late_transcript_extends_user_bubble_without_moving_reply(final_ms, expected_end):
    take = {'durationMs': 20000, 'events': [
        {'type': 'user-start', 'utterance': 'u1', 'voice': 'lux', 'atMs': 2530, 'sequence': 1},
        {'type': 'user-end', 'utterance': 'u1', 'atMs': 11522, 'sequence': 2},
        {'type': 'agent-start', 'clip': 'lux-1', 'atMs': 13682, 'sequence': 3},
    ]}
    capture = {'utterances': {'u1': {'updates': [], 'final': 'Find a partial name.', 'finalAtMs': final_ms}}}

    revised = with_streaming_transcripts(take, capture)

    assert {e['type']: e['atMs'] for e in revised['events'] if e['type'] != 'transcript'} == {
        'user-start': 2530, 'user-end': expected_end, 'agent-start': 13682,
    }
    assert take['events'][1]['atMs'] == 11522


def test_work_waits_for_user_and_disappears_if_no_pause_remains():
    take = {'events': [
        {'type': 'user-start', 'utterance': 'u1', 'atMs': 2500},
        {'type': 'user-end', 'utterance': 'u1', 'atMs': 12712},
    ]}
    blocks = [
        {'id': 'b1', 'startMs': 11522, 'endMs': 13648, 'status': 'thinking'},
        {'id': 'b2', 'startMs': 12000, 'endMs': 12500, 'status': 'console'},
        {'id': 'b3', 'startMs': 18000, 'endMs': 19000, 'status': 'console'},
    ]

    assert align_activities(blocks, take) == [
        {'id': 'b1', 'startMs': 12712, 'endMs': 13648, 'status': 'thinking'},
        blocks[2],
    ]
