import os

from noisy_studio.listener import audio_cache
from noisy_studio.listener.audio_cache import AudioCache


def test_put_then_get_returns_the_same_bytes():
    cache = AudioCache(directory=None)
    clip_key = audio_cache.key(7, "hello", "carina", "auto", 1.0)

    cache.put(clip_key, b"mp3-bytes")

    assert cache.get(clip_key) == b"mp3-bytes"


def test_get_misses_for_an_unknown_key():
    cache = AudioCache(directory=None)

    assert cache.get(audio_cache.key(7, "hello", "carina", "auto", 1.0)) is None


def test_key_requires_a_stable_card_identity():
    assert audio_cache.key(0, "hello", "carina", "auto", 1.0) is None


def test_key_changes_with_every_render_parameter():
    base = audio_cache.key(7, "hello", "carina", "auto", 1.0)

    assert audio_cache.key(7, "goodbye", "carina", "auto", 1.0) != base
    assert audio_cache.key(7, "hello", "rex", "auto", 1.0) != base
    assert audio_cache.key(7, "hello", "carina", "pl", 1.0) != base
    assert audio_cache.key(7, "hello", "carina", "auto", 1.2) != base
    assert audio_cache.key(8, "hello", "carina", "auto", 1.0) != base


def test_none_key_and_empty_audio_are_ignored():
    cache = AudioCache(directory=None)

    cache.put(None, b"mp3-bytes")
    cache.put(audio_cache.key(7, "hello", "carina", "auto", 1.0), b"")

    assert cache.get(audio_cache.key(7, "hello", "carina", "auto", 1.0)) is None


def test_memory_evicts_the_oldest_clip_beyond_the_count_bound(monkeypatch):
    monkeypatch.setattr(audio_cache, "MEMORY_MAX_CLIPS", 2)
    cache = AudioCache(directory=None)
    keys = [audio_cache.key(i, f"clip {i}", "carina", "auto", 1.0) for i in (1, 2, 3)]

    for clip_key in keys:
        cache.put(clip_key, b"mp3-bytes")

    assert cache.get(keys[0]) is None
    assert cache.get(keys[1]) == b"mp3-bytes"
    assert cache.get(keys[2]) == b"mp3-bytes"


def test_memory_evicts_by_total_bytes(monkeypatch):
    monkeypatch.setattr(audio_cache, "MEMORY_MAX_BYTES", 10)
    cache = AudioCache(directory=None)
    first = audio_cache.key(1, "one", "carina", "auto", 1.0)
    second = audio_cache.key(2, "two", "carina", "auto", 1.0)

    cache.put(first, b"123456")
    cache.put(second, b"789012")

    assert cache.get(first) is None
    assert cache.get(second) == b"789012"


def test_clips_survive_a_restart_through_the_disk_tier(tmp_path):
    clip_key = audio_cache.key(7, "hello", "carina", "auto", 1.0)
    AudioCache(directory=tmp_path).put(clip_key, b"mp3-bytes")

    fresh_instance = AudioCache(directory=tmp_path)

    assert fresh_instance.get(clip_key) == b"mp3-bytes"


def test_disk_evicts_the_oldest_file_beyond_the_count_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_cache, "DISK_MAX_CLIPS", 2)
    cache = AudioCache(directory=tmp_path)
    keys = [audio_cache.key(i, f"clip {i}", "carina", "auto", 1.0) for i in (1, 2, 3)]

    for index, clip_key in enumerate(keys):
        cache.put(clip_key, b"mp3-bytes")
        # Distinct mtimes so "oldest" is well-defined on coarse filesystems.
        os.utime(tmp_path / f"{clip_key}.mp3", (index + 1, index + 1))

    cache.put(keys[2], b"mp3-bytes")  # over the bound — the oldest file goes

    remaining = {path.name for path in tmp_path.glob("*.mp3")}
    assert remaining == {f"{keys[1]}.mp3", f"{keys[2]}.mp3"}


def test_memory_only_cache_writes_no_files(tmp_path):
    cache = AudioCache(directory=None)

    cache.put(audio_cache.key(7, "hello", "carina", "auto", 1.0), b"mp3-bytes")

    assert list(tmp_path.iterdir()) == []


def test_provider_changes_do_not_reuse_the_previous_voice_audio():
    keys = {audio_cache.key(1, 'Hello', 'voice1', 'en', 1.0, provider)
            for provider in ('cloud:model1', 'local:model2', 'local:model3')}

    assert len(keys) == 3


def test_wav_replay_keeps_its_format_after_restart(tmp_path):
    from noisy_studio.providers.base import SynthesizedAudio

    clip = SynthesizedAudio(b'RIFF-audio', 'audio/wav', 2.4)
    AudioCache(directory=tmp_path).put_audio('clip1', clip)

    assert AudioCache(directory=tmp_path).get_audio('clip1') == clip
