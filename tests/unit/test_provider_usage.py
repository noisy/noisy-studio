from types import SimpleNamespace

from noisy_studio.listener.provider_usage import ProviderUsage, parse_windows


def test_codex_primary_weekly_is_not_mislabelled_as_session():
    assert parse_windows('codex', {'rateLimits': {'primary': {'usedPercent': 61, 'windowDurationMins': 10080, 'resetsAt': 900}, 'secondary': None}}) == [
        {'label': 'Weekly', 'used_percent': 61, 'resets_at': 900},
    ]


def test_claude_missing_window_and_invalid_percentage_do_not_become_zero():
    assert parse_windows('claude', {'five_hour': {'used_percentage': float('nan'), 'resets_at': 900}, 'seven_day': None}) == []


def registry():
    conversations = {'c1': SimpleNamespace(harness='claude-hooks', hidden=False, ended=False), 'c2': SimpleNamespace(harness='claude-hooks', hidden=False, ended=False)}
    return SimpleNamespace(resolve=lambda key: key if key in conversations else None, get=conversations.get)


def test_reports_deduplicate_known_scope_and_expire_each_window_independently():
    usage = ProviderUsage(clock=lambda: 1000)
    data = {'five_hour': {'used_percentage': 90, 'resets_at': 999}, 'seven_day': {'used_percentage': 20, 'resets_at': 2000}}
    for key in ('c1', 'c2'):
        usage.record(registry(), key, 'claude', 'a' * 64, data)
    result = usage.snapshot({key: {'harness': 'claude-hooks', 'status': 'idle'} for key in ('c1', 'c2')})
    assert result == [{'provider': 'claude', 'label': 'Claude', 'sampled_at': 1000, 'scope': 'connection', 'message': '', 'windows': [
        {'label': 'Session', 'used_percent': 90, 'resets_at': 999, 'stale': True},
        {'label': 'Weekly', 'used_percent': 20, 'resets_at': 2000, 'stale': False},
    ]}]


def test_registered_provider_only_and_closed_conversations_are_excluded():
    usage = ProviderUsage()
    assert usage.snapshot({'c1': {'harness': 'claude-hooks', 'hidden': True}, 'c2': {'harness': 'codex-hooks', 'status': 'ended'}, 'c3': {'harness': 'grok', 'status': 'live'}}) == [
        {'provider': 'grok', 'label': 'Grok', 'sampled_at': None, 'scope': 'unknown', 'message': 'Usage unavailable', 'windows': []},
    ]


def test_unregistered_or_wrong_provider_cannot_publish_usage():
    usage = ProviderUsage()
    assert [usage.record(registry(), key, provider, 'a' * 64, {}) for key, provider in [('c3', 'claude'), ('c1', 'codex')]] == [False, False]


def test_new_sample_removes_independently_absent_window():
    usage = ProviderUsage(clock=lambda: 1000)
    usage.record(registry(), 'c1', 'claude', 'a' * 64, {'five_hour': {'used_percentage': 50, 'resets_at': 2000}})
    usage.record(registry(), 'c1', 'claude', 'a' * 64, {})
    assert usage.snapshot({'c1': {'harness': 'claude-hooks'}})[0]['windows'] == []


def test_matching_registered_profile_uses_one_report_for_other_conversations():
    usage = ProviderUsage(clock=lambda: 1000)
    usage.bind('c2', 'a' * 64)
    usage.record(registry(), 'c1', 'claude', 'a' * 64, {'five_hour': {'used_percentage': 50, 'resets_at': 2000}})
    assert len(usage.snapshot({key: {'harness': 'claude-hooks'} for key in ('c1', 'c2')})) == 1
