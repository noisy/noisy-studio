import importlib.util
import json
from pathlib import Path
import sys


def collector():
    spec = importlib.util.spec_from_file_location('usage_collector_test', Path(__file__).parents[2] / 'hooks' / '_provider_usage.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_app_server_handshake_reads_limits_without_starting_a_turn(tmp_path):
    script = tmp_path / 'server.py'
    log = tmp_path / 'calls.json'
    script.write_text('''import json,sys
calls=[]
for line in sys.stdin:
 message=json.loads(line); calls.append(message['method'])
 if message['method']=='initialize': print(json.dumps({'id':1,'result':{}}),flush=True)
 if message['method']=='account/rateLimits/read':
  open(sys.argv[1],'w').write(json.dumps(calls))
  print(json.dumps({'id':2,'result':{'rateLimits':{'primary':None}}}),flush=True)
''')
    result = collector().read_codex_limits([sys.executable, str(script), str(log)], timeout=2)
    assert {'result': result, 'calls': json.loads(log.read_text())} == {
        'result': {'rateLimits': {'primary': None}},
        'calls': ['initialize', 'initialized', 'account/rateLimits/read'],
    }


def test_collector_timeout_is_bounded_when_server_never_answers(tmp_path):
    script = tmp_path / 'server.py'
    script.write_text('import time; time.sleep(10)')
    assert collector().read_codex_limits([sys.executable, str(script)], timeout=0.05) is None


def test_profile_scope_is_opaque_and_separates_profiles(monkeypatch):
    module = collector()
    monkeypatch.setenv('CODEX_HOME', '/example/profile1')
    first = module.connection_scope('codex')
    monkeypatch.setenv('CODEX_HOME', '/example/profile2')
    second = module.connection_scope('codex')
    assert (len(first), len(second), first == second, 'example' in first) == (64, 64, False, False)


def test_statusline_forwards_only_quota_fields_and_preserves_existing_command(monkeypatch):
    import io
    hooks = Path(__file__).parents[2] / 'hooks'
    monkeypatch.syspath_prepend(str(hooks))
    spec = importlib.util.spec_from_file_location('statusline_test', hooks / 'claude_statusline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    body = {'session_id': 'c1', 'rate_limits': {'seven_day': {'used_percentage': 30}}, 'unrelated': 'not forwarded'}
    raw = json.dumps(body)
    published = []
    chained = []
    monkeypatch.setattr(module._client, 'post', lambda path, data, **kwargs: published.append((path, data['conversation'], data['data'])))
    monkeypatch.setattr(module.subprocess, 'run', lambda args, **kwargs: chained.append((args, kwargs['input'])))
    monkeypatch.setattr(sys, 'stdin', io.StringIO(raw))
    monkeypatch.setattr(sys, 'argv', ['claude_statusline.py', '--', 'existing-statusline', '--compact'])
    module.main()
    assert {'published': published, 'chained': chained} == {
        'published': [('/provider-usage', 'c1', body['rate_limits'])],
        'chained': [(['existing-statusline', '--compact'], raw)],
    }
