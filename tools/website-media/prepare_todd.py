"""Build synchronized delivery copies from Todd's untouched camera and Studio exports."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from transcript_timing import with_streaming_transcripts, with_crew_focus

ROOT = Path(__file__).resolve().parents[2]
# Camera time = browser MediaRecorder time + offset. Waveform correlation of
# every actor turn agrees within 0.3 ms; no clock stretch is needed.
SCENES = [('hero', 'hero-search', 'Hero Search', 3.609375), ('crew', 'crew', 'Crew', 3.109375)]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('delivery', type=Path)
    args = parser.parse_args()
    output = ROOT / 'website/src/assets/todd'
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'sources': [], 'settings': {'video': '854x480 H.264 CRF24', 'audio': 'actor microphone + original agent clips, AAC128k', 'sync': 'constant waveform alignment; no stretch'}}
    for scene, prefix, title, offset in SCENES:
        camera = args.delivery / f'Todd - {title}.mp4'
        journal, = args.delivery.glob(prefix + '*.json')
        reference = journal.with_suffix('.webm')
        sources = [camera, journal, reference]
        before = {p.name: digest(p) for p in sources}
        take = json.loads(journal.read_text())
        duration = take['durationMs'] / 1000
        command = ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-ss', str(offset), '-i', str(camera)]
        replies = [e for e in take['events'] if e['type'] == 'agent-start']
        for e in replies:
            folder = ROOT / ('tools/demo-recorder/clips' if e['clip'].startswith('hero-lux-') else 'dashboard/src/components/marketing/crew-voice')
            command += ['-i', str(folder / (e['clip'] + '.mp3'))]
        filters = ['[0:v]setpts=PTS-STARTPTS,scale=854:480:flags=lanczos[v]', '[0:a]asetpts=PTS-STARTPTS[a0]']
        for i, event in enumerate(replies, 1):
            filters.append(f'[{i}:a]adelay={event["atMs"]:.3f}:all=1[a{i}]')
        filters.append(''.join(f'[a{i}]' for i in range(len(replies)+1)) + f'amix=inputs={len(replies)+1}:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[a]')
        video = output / f'{scene}.mp4'
        command += ['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(duration),'-c:v','libx264','-preset','slow','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(video)]
        subprocess.run(command, check=True)
        subprocess.run(['ffmpeg','-v','error','-y','-ss','2','-i',str(video),'-frames:v','1',str(output/f'{scene}-poster.jpg')],check=True)
        # Use the delivered timeline, not the old actor's presentation edits.
        if scene == 'crew':
            take = with_crew_focus(take)
        capture = output / f'{scene}-transcripts.json'
        displayed_take = with_streaming_transcripts(take, json.loads(capture.read_text())) if capture.exists() else take
        (output/f'{scene}.json').write_text(json.dumps(displayed_take,indent=2)+'\n')
        activities = []
        tasks = {'Reading src/search.ts':'u1','Editing src/search.ts':'u2','Running tests':'u3','Deploying to production':'u4'}
        for e in take['events']:
            if e['type'] != 'activity-start': continue
            end = next(x for x in take['events'] if x['type']=='activity-end' and x['atMs'] > e['atMs'])
            activities.append({'id':f'activity-{e["sequence"]}','startMs':e['atMs'],'endMs':end['atMs'],'status':'console' if e.get('text') in tasks else 'thinking', **({'consoleTask':tasks[e['text']]} if e.get('text') in tasks else {})})
        (output/f'{scene}-activities.json').write_text(json.dumps(activities,indent=2)+'\n')
        assert before == {p.name:digest(p) for p in sources}, 'Original modified'
        manifest['sources'].append({'scene':scene,'source_directory':str(args.delivery),'sha256':before,'camera_offset_seconds':offset,'duration_seconds':duration,'output_bytes':video.stat().st_size,'output_sha256':digest(video)})
        print(scene,video.stat().st_size,'bytes',flush=True)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__ == '__main__': main()
