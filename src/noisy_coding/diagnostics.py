"""Independent live checks of every xAI call the plugin makes.

One check per call site, each reporting its own pass/fail — never a single
verdict. That distinction is the whole point: xAI's voice endpoints have
rejected VALID keys intermittently (HTTP 400 "Incorrect API key" while
/api-key and chat passed), and a lone red light next to a green api_key
check tells the user "service degraded, not your key" instead of sending
them off to rotate a working credential.

Every probe exercises the plugin's REAL call path (tts.synthesize,
stt.transcribe, the streaming handshakes), so a green check means that
feature actually works — not that some unrelated endpoint answered.
"""

from noisy_coding import environment
import asyncio
import os
import time
from collections.abc import Awaitable, Callable

import httpx
import numpy as np
import websockets

from noisy_coding import tts, tts_stream
from noisy_coding.listener import stt, stt_stream

CHECK_TIMEOUT_SECONDS = 10.0
# Presentation pacing (Krzysztof's spec): checks run SEQUENTIALLY and each
# verdict stays on screen at least this long — a sub-second cascade reads
# as an unreadable flash, not a verification the user can trust.
MIN_CHECK_SECONDS = 1.0
PROBE_TEXT = "ok"  # two paid TTS characters — the cheapest real synthesis
PROBE_VOICE = "eve"
PROBE_SAMPLE_RATE = 16_000
PROBE_SILENCE_SAMPLES = 1_600  # 0.1 s — the smallest WAV worth transcribing
# Same env vars the daemon's credits poller uses (see daemon._poll_credits).
MANAGEMENT_KEY_ENV_VAR = "NOISY_CODING_MANAGEMENT_KEY"
TEAM_ID_ENV_VAR = "NOISY_CODING_TEAM_ID"
BILLING_URL_TEMPLATE = (
    "https://management-api.x.ai/v1/billing/teams/{team_id}/prepaid/balance"
)


def _auth_header() -> dict:
    return {"Authorization": f"Bearer {tts._api_key()}"}


async def _check_api_key() -> None:
    """Is the key valid at all (ACLs/scopes readable)?"""
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_SECONDS) as client:
        response = await client.get(f"{tts.XAI_API_BASE}/api-key", headers=_auth_header())
    if response.status_code != httpx.codes.OK:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")


async def _check_tts_batch() -> None:
    """The exact path speak/announce renders through (tts.py)."""
    await tts.synthesize(PROBE_TEXT, PROBE_VOICE, "auto", 1.0)


async def _check_tts_stream() -> None:
    """Live-mode TTS handshake (tts_stream.py) — auth happens at connect."""
    query = f"language=auto&voice={PROBE_VOICE}&codec=mp3&speed=1.0"
    async with websockets.connect(
        f"{tts_stream.STREAM_URL_BASE}?{query}",
        additional_headers=_auth_header(),
        open_timeout=CHECK_TIMEOUT_SECONDS,
    ):
        pass  # the accepted handshake IS the check


async def _check_stt_batch() -> None:
    """The exact path batch transcription uses (stt.py), with a tiny WAV."""
    silence = np.zeros(PROBE_SILENCE_SAMPLES, dtype=np.int16)
    await asyncio.to_thread(stt.transcribe, stt.encode_wav(silence, PROBE_SAMPLE_RATE))


async def _check_stt_stream() -> None:
    """Live-mode STT handshake (stt_stream.py)."""

    def handshake() -> None:
        from websockets.sync.client import connect

        with connect(
            f"{stt_stream.STREAM_URL_BASE}?sample_rate={PROBE_SAMPLE_RATE}&encoding=pcm",
            additional_headers=_auth_header(),
            open_timeout=CHECK_TIMEOUT_SECONDS,
        ):
            pass

    await asyncio.to_thread(handshake)


async def _check_voices() -> None:
    """The dashboard's voice picker source."""
    await tts.list_voices()


async def _check_billing() -> None:
    """Credits display (only when a management key/team id is configured)."""
    url = BILLING_URL_TEMPLATE.format(team_id=environment.get(TEAM_ID_ENV_VAR))
    headers = {"Authorization": f"Bearer {environment.get(MANAGEMENT_KEY_ENV_VAR)}"}
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=headers)
    if response.status_code != httpx.codes.OK:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")


CHECKS: dict[str, Callable[[], Awaitable[None]]] = {
    "api_key": _check_api_key,
    "tts_batch": _check_tts_batch,
    "tts_stream": _check_tts_stream,
    "stt_batch": _check_stt_batch,
    "stt_stream": _check_stt_stream,
    "voices": _check_voices,
}


ProgressCallback = Callable[[dict[str, dict]], None]


async def run_checks(on_progress: ProgressCallback | None = None) -> dict[str, dict]:
    """Run the checks one by one; each result stands alone.

    A failure in one must never be read as "the key is bad" when others
    pass — the caller renders them separately, verbatim.

    `on_progress` fires with the full (partial) result map: once up front
    with every check pending, then after each completion — so a UI polling
    it shows verdicts landing line by line, top to bottom, at a pace a
    human can actually follow (MIN_CHECK_SECONDS each).
    """
    checks = dict(CHECKS)
    if environment.get(MANAGEMENT_KEY_ENV_VAR) and environment.get(TEAM_ID_ENV_VAR):
        checks["billing"] = _check_billing

    results: dict[str, dict] = {name: {"pending": True} for name in checks}

    def report() -> None:
        if on_progress:
            on_progress({name: dict(result) for name, result in results.items()})

    report()
    for name, check in checks.items():
        started = time.monotonic()
        try:
            await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
            results[name] = {"ok": True, "ms": int((time.monotonic() - started) * 1000)}
        except Exception as error:
            results[name] = {"ok": False, "detail": str(error)[:300]}
        remaining = MIN_CHECK_SECONDS - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)
        report()
    return results


def run_checks_sync(on_progress: ProgressCallback | None = None) -> dict[str, dict]:
    """run_checks for synchronous callers (the HTTP handler threads)."""
    return asyncio.run(run_checks(on_progress))
