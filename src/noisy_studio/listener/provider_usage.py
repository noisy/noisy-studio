"""Account quota observations scoped to registered conversations in this daemon."""
from __future__ import annotations

import math
import re
import threading
import time

from noisy_studio.harness.provider import provider_name

STALE_AFTER_SECONDS = 300
LABELS = {'claude': 'Claude', 'codex': 'Codex', 'grok': 'Grok'}


def _window(label, used, reset):
    if isinstance(used, bool) or not isinstance(used, (int, float)) or not math.isfinite(used) or not 0 <= used <= 100:
        return None
    if isinstance(reset, bool) or not isinstance(reset, (int, float)) or not math.isfinite(reset) or reset <= 0:
        reset = None
    return {'label': label, 'used_percent': used, 'resets_at': reset}


def parse_windows(provider: str, data: dict) -> list[dict]:
    result = []
    if provider == 'claude':
        for key, label in [('five_hour', 'Session'), ('seven_day', 'Weekly')]:
            row = data.get(key)
            if isinstance(row, dict):
                window = _window(label, row.get('used_percentage'), row.get('resets_at'))
                if window:
                    result.append(window)
    elif provider == 'codex':
        buckets = data.get('rateLimitsByLimitId')
        snapshots = list(buckets.values()) if isinstance(buckets, dict) and buckets else [data.get('rateLimits', data)]
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            # Limit names may identify models; never surface arbitrary account data.
            name = snapshot.get('limitName')
            suffix = f' · {name}' if isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9 ._-]{1,32}', name) else ''
            for key in ('primary', 'secondary'):
                row = snapshot.get(key)
                if not isinstance(row, dict):
                    continue
                duration = row.get('windowDurationMins')
                label = {300: 'Session', 10080: 'Weekly'}.get(duration, 'Window') if isinstance(duration, (int, float)) else 'Window'
                window = _window(label + suffix, row.get('usedPercent'), row.get('resetsAt'))
                if window and window not in result:
                    result.append(window)
    return result


class ProviderUsage:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._lock = threading.Lock()
        self._reports: dict[str, dict] = {}
        self._scopes: dict[str, str] = {}

    def bind(self, conversation: str, scope: str) -> None:
        if isinstance(scope, str) and re.fullmatch(r'[a-f0-9]{64}', scope):
            with self._lock:
                self._scopes[conversation] = scope

    def record(self, registry, conversation: str, provider: str, scope: str, data: dict) -> bool:
        key = registry.resolve(conversation)
        registered = registry.get(key) if key else None
        if registered is None or registered.hidden or registered.ended or provider_name(registered.harness) != provider:
            return False
        if provider not in ('claude', 'codex') or not re.fullmatch(r'[a-f0-9]{64}', scope):
            return False
        windows = parse_windows(provider, data)
        with self._lock:
            # Replace the sample: an absent window is not a zero or a fresh old value.
            self._scopes[key] = scope
            self._reports[key] = {'scope': scope, 'provider': provider, 'sampled_at': self._clock(), 'windows': windows}
        return True

    def snapshot(self, conversations: dict) -> list[dict]:
        now = self._clock()
        with self._lock:
            reports = dict(self._reports)
            scopes = dict(self._scopes)
        groups = {}
        for key, conversation in conversations.items():
            provider = provider_name(conversation['harness'])
            if provider == 'legacy':
                provider = conversation.get('usage_provider')
            if provider not in LABELS or conversation.get('hidden') or conversation.get('status') == 'ended':
                continue
            scope = scopes.get(key)
            candidates = [item for item in reports.values() if item['provider'] == provider and item['scope'] == scope]
            report = max(candidates, key=lambda item: item['sampled_at']) if candidates else None
            # Profile hashes deduplicate observations only within a known connection
            # scope. Unknown profiles must not be assumed to share one account.
            group_key = (provider, report['scope'] if report else 'unknown')
            if group_key in groups and (not report or groups[group_key]['sampled_at'] >= report['sampled_at']):
                continue
            sampled_at = report['sampled_at'] if report else 0
            windows = []
            for window in report['windows'] if report else []:
                stale = now - sampled_at > STALE_AFTER_SECONDS or bool(window['resets_at'] and now >= window['resets_at'])
                windows.append({**window, 'stale': stale})
            groups[group_key] = {'provider': provider, 'label': LABELS[provider], 'sampled_at': sampled_at or None,
                                 'windows': windows, 'scope': 'connection' if report else 'unknown',
                                 'message': '' if windows else ('Usage unavailable' if provider == 'grok' else 'Waiting for usage data')}
        # No profile identifiers or conversation IDs cross the presentation boundary.
        return list(groups.values())
