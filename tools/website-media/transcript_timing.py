"""Apply captured STT updates without moving video or scenario boundaries."""
from copy import deepcopy


def with_streaming_transcripts(take, capture):
    result = deepcopy(take)
    result['events'] = [event for event in result['events'] if event['type'] != 'transcript']
    for identity, transcript in capture['utterances'].items():
        start = next(e for e in result['events'] if e['type'] == 'user-start' and e['utterance'] == identity)
        end = next(e for e in result['events'] if e['type'] == 'user-end' and e['utterance'] == identity)
        for index, update in enumerate(transcript['updates']):
            # Grok can briefly repeat a merged segment. Keep the previous
            # caption until it settles; preserve the raw update in the capture.
            if len(update['text'].split()) > len(transcript['final'].split()) * 1.5:
                continue
            result['events'].append({
                'type': 'transcript', 'utterance': identity, 'voice': start['voice'],
                'text': update['text'], 'final': False,
                'atMs': max(start['atMs'], min(update['receivedAtMs'], result['durationMs'])),
                'sequence': end['sequence'] - 0.5 + index / (2 * (len(transcript['updates']) + 1)),
            })
        result['events'].append({
            'type': 'transcript', 'utterance': identity, 'voice': start['voice'],
            'text': transcript['final'], 'final': True,
            'atMs': min(transcript['finalAtMs'], result['durationMs']), 'sequence': 1000000,
        })
    result['events'].sort(key=lambda event: (event['atMs'], event['sequence']))
    for sequence, event in enumerate(result['events'], 1):
        event['sequence'] = sequence
    result['transcriptSource'] = 'xAI Grok streaming STT from actor camera audio'
    result['transcriptOffsetsMs'] = {}
    if 'presentation' in result:
        result['presentation'] = [dict(event, displayAtMs=event['atMs']) for event in result['events']]
    return result


if __name__ == '__main__':
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[2] / 'website/src/assets/todd'
    manifest = json.loads((folder / 'manifest.json').read_text())
    for source in manifest['sources']:
        scene = source['scene']
        journal = next(name for name in source['sha256'] if name.endswith('.json'))
        original = json.loads((Path(source['source_directory']) / journal).read_text())
        capture = json.loads((folder / f'{scene}-transcripts.json').read_text())
        revised = with_streaming_transcripts(original, capture)
        (folder / f'{scene}.json').write_text(json.dumps(revised, indent=2) + '\n')
