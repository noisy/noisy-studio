import asyncio
import time

import pytest

from noisy_studio import diagnostics


@pytest.fixture(autouse=True)
def instant_pacing(monkeypatch):
    """Verdict tests care about results, not the 1 s presentation cadence."""
    monkeypatch.setattr(diagnostics, "MIN_CHECK_SECONDS", 0)


def test_each_check_reports_its_own_verdict(monkeypatch):
    async def passing():
        pass

    async def failing():
        raise RuntimeError("HTTP 400: Incorrect API key")

    monkeypatch.setattr(
        diagnostics, "CHECKS", {"api_key": passing, "tts_stream": failing}
    )

    results = diagnostics.run_checks_sync()

    assert results["api_key"]["ok"] is True
    assert isinstance(results["api_key"]["ms"], int)
    assert results["tts_stream"]["ok"] is False
    assert "Incorrect API key" in results["tts_stream"]["detail"]


def test_one_failing_check_does_not_poison_the_others(monkeypatch):
    async def passing():
        pass

    async def exploding():
        raise ConnectionError("peer closed")

    monkeypatch.setattr(
        diagnostics,
        "CHECKS",
        {"a": passing, "b": exploding, "c": passing},
    )

    results = diagnostics.run_checks_sync()

    assert [results[name]["ok"] for name in ("a", "b", "c")] == [True, False, True]


def test_hung_check_fails_by_timeout_instead_of_blocking(monkeypatch):
    async def hangs():
        await asyncio.sleep(60)

    monkeypatch.setattr(diagnostics, "CHECK_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(diagnostics, "CHECKS", {"stt_stream": hangs})

    results = diagnostics.run_checks_sync()

    assert results["stt_stream"]["ok"] is False


def test_progress_reports_verdicts_as_they_land(monkeypatch):
    async def passing():
        pass

    async def failing():
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(diagnostics, "CHECKS", {"a": passing, "b": failing})
    snapshots = []

    results = diagnostics.run_checks_sync(snapshots.append)

    # First snapshot: everything pending; later ones fill in one by one.
    assert snapshots[0] == {"a": {"pending": True}, "b": {"pending": True}}
    assert len(snapshots) == 3  # initial + one per completed check
    assert snapshots[-1] == results
    assert results["a"]["ok"] is True
    assert results["b"]["ok"] is False


def test_billing_check_runs_only_when_configured(monkeypatch):
    async def passing():
        pass

    monkeypatch.setattr(diagnostics, "CHECKS", {"api_key": passing})
    monkeypatch.delenv(diagnostics.MANAGEMENT_KEY_ENV_VAR, raising=False)
    monkeypatch.delenv(diagnostics.TEAM_ID_ENV_VAR, raising=False)
    assert "billing" not in diagnostics.run_checks_sync()

    monkeypatch.setenv(diagnostics.MANAGEMENT_KEY_ENV_VAR, "mk")
    monkeypatch.setenv(diagnostics.TEAM_ID_ENV_VAR, "team")

    async def fake_billing():
        pass

    monkeypatch.setattr(diagnostics, "_check_billing", fake_billing)
    assert "billing" in diagnostics.run_checks_sync()


def test_each_verdict_stays_on_screen_at_least_the_pacing_interval(monkeypatch):
    async def instant():
        pass

    monkeypatch.setattr(diagnostics, "MIN_CHECK_SECONDS", 0.1)
    monkeypatch.setattr(diagnostics, "CHECKS", {"a": instant, "b": instant})
    stamps = []

    diagnostics.run_checks_sync(lambda _snapshot: stamps.append(time.monotonic()))

    # initial, then one per check — each at least the pacing interval apart.
    assert len(stamps) == 3
    assert stamps[1] - stamps[0] >= 0.1
    assert stamps[2] - stamps[1] >= 0.1
