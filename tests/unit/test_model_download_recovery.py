from contextlib import contextmanager
import sys
from types import ModuleType

import pytest

from noisy_studio.providers import downloads, local
from noisy_studio.providers.base import TTSError


@pytest.mark.parametrize('chunks,total', [([b'part'], 20), ([], 0)])
def test_incomplete_model_is_never_published_and_retry_recovers(tmp_path, monkeypatch, chunks, total):
    monkeypatch.setattr('noisy_studio.config_dir.CONFIG_DIR', tmp_path)
    class Response:
        headers = {'content-length': str(total)}
        def raise_for_status(self):
            pass
        def iter_bytes(self):
            return iter(chunks)
    @contextmanager
    def response(*args, **kwargs):
        yield Response()
    monkeypatch.setattr(local.httpx, 'stream', response)
    target = tmp_path / 'models' / 'kokoro' / 'recovery-test.onnx'

    with pytest.raises(TTSError, match='incomplete'):
        local._ensure_downloaded('https://example.invalid/model', target.name)

    assert {'published': target.exists(), 'partial': target.with_suffix('.onnx.part').exists(),
            'state': next(d['state'] for d in downloads.status() if d['name']==target.name)} == {
                'published': False, 'partial': False, 'state': 'error'}
    chunks[:] = [b'complete-model']
    Response.headers = {'content-length': str(len(chunks[0]))}
    restored = local._ensure_downloaded('https://example.invalid/model', target.name)
    assert restored.read_bytes() == b'complete-model'


def test_recognition_cache_requires_configuration_and_tokenizer_for_offline_use(tmp_path, monkeypatch):
    hub = ModuleType('huggingface_hub')
    hub.try_to_load_from_cache = lambda *args, **kwargs: str(tmp_path / 'model.bin')
    monkeypatch.setitem(sys.modules, 'huggingface_hub', hub)
    (tmp_path / 'model.bin').write_bytes(b'weights')
    assert local._whisper_cached('base') is False
    (tmp_path / 'config.json').write_text('{}')
    (tmp_path / 'tokenizer.json').write_text('{}')
    assert local._whisper_cached('base') is True
