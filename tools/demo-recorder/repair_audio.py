"""Replace marked microphone intervals with room tone without moving any samples."""

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

CROSSFADE_MS = 12


def validate_source(source: Path, plan: dict):
    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if (plan.get('kind') != 'demo-audio-edits' or plan.get('version') != 1
            or plan['source']['sha256'] != digest or plan['source']['size'] != source.stat().st_size):
        raise ValueError('Audio markers do not match the original recording.')


def sample_ranges(plan, sample_rate, sample_count, external_tone=False):
    def bounds(interval):
        start, end = interval['startMs'], interval['endMs']
        if (type(start) is not int or type(end) is not int or start < 0 or end <= start
                or end > sample_count / sample_rate * 1000 + 1):
            raise ValueError('Audio interval is outside the original recording.')
        return round(start * sample_rate / 1000), min(sample_count, round(end * sample_rate / 1000))

    if not plan.get('roomTone'):
        raise ValueError('Choose a clean room-tone reference before repairing audio.')
    tone = bounds(plan['roomTone'])
    ranges = sorted(bounds(interval) for interval in plan['repairs'])
    for index, (start, end) in enumerate(ranges):
        if index and start < ranges[index - 1][1]:
            raise ValueError('Repair intervals overlap.')
        if not external_tone and start < tone[1] and tone[0] < end:
            raise ValueError('Room tone overlaps a repair interval.')
    return tone, ranges


def loop_room_tone(tone, length, fade_samples):
    fade = min(fade_samples, len(tone) // 2)
    if not fade:
        raise ValueError('Room-tone reference is too short.')
    result = tone.copy()
    ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    while len(result) < length:
        seam = result[-fade:] * (1 - ramp) + tone[:fade] * ramp
        result = np.concatenate((result[:-fade], seam, tone[fade:]))
    return result[:length]


def replace_intervals(samples, sample_rate, plan, external_tone=None):
    tone_range, ranges = sample_ranges(plan, sample_rate, len(samples), external_tone is not None)
    tone = samples[slice(*tone_range)] if external_tone is None else external_tone
    # Adjacent repairs form one gap: do not fade the unwanted original back
    # in at internal boundaries (including the replaced room-tone interval).
    merged = []
    for start, end in ranges:
        if merged and start == merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    if external_tone is not None:
        ranges = merged
    output = samples.copy()
    fade_samples = max(1, round(CROSSFADE_MS * sample_rate / 1000))
    for start, end in ranges:
        replacement = loop_room_tone(tone, end - start, fade_samples)
        fade = min(fade_samples, len(replacement) // 2)
        weight = np.ones((len(replacement), 1), dtype=np.float32)
        if fade:
            ramp = np.linspace(0, 1, fade, dtype=np.float32)
            weight[:fade, 0] = ramp
            weight[-fade:, 0] = ramp[::-1]
        output[start:end] = samples[start:end] * (1 - weight) + replacement * weight
    return output


def repair_microphone(source: Path, plan_path: Path, destination: Path, room_tone_reference=None):
    plan = json.loads(plan_path.read_text())
    validate_source(source, plan)
    info = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=sample_rate,channels', '-of', 'json', str(source),
    ]))['streams'][0]
    sample_rate, channels = int(info['sample_rate']), info['channels']
    raw = subprocess.check_output([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source),
        '-map', '0:a:0', '-f', 'f32le', '-acodec', 'pcm_f32le', '-',
    ])
    samples = np.frombuffer(raw, dtype='<f4').reshape(-1, channels)
    external_tone = None
    if room_tone_reference is not None:
        tone_source, tone_plan_path = room_tone_reference
        tone_plan = json.loads(tone_plan_path.read_text())
        validate_source(tone_source, tone_plan)
        tone_audio = subprocess.check_output([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(tone_source),
            '-map', '0:a:0', '-ar', str(sample_rate), '-ac', str(channels),
            '-f', 'f32le', '-acodec', 'pcm_f32le', '-',
        ])
        tone_samples = np.frombuffer(tone_audio, dtype='<f4').reshape(-1, channels)
        tone_range, _ = sample_ranges(tone_plan, sample_rate, len(tone_samples))
        external_tone = tone_samples[slice(*tone_range)]
        # The rejected crew reference must be repaired as well.
        plan['repairs'].append(dict(plan['roomTone']))
    repaired = replace_intervals(samples, sample_rate, plan, external_tone)
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'f32le',
        '-ar', str(sample_rate), '-ac', str(channels), '-i', '-',
        '-c:a', 'pcm_f32le', str(destination),
    ], input=repaired.astype('<f4').tobytes(), check=True)
    print(f'Replaced {len(plan["repairs"])} microphone intervals; preserved {len(samples)} samples at {sample_rate} Hz.')
