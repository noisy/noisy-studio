"""Speech-to-text test bench data layer (day 4, v2).

Each archived utterance WAV is a TEST: it carries an EXPECTED transcript
(blessed from a previous run) and can be re-run through the batch or the
live pipeline. The status page fires the runs in parallel - one small
request per recording per pipeline - and renders each diff as it lands.

Endpoints (wired in http_api.py):
    GET  /tests/speech        list tests: file, seconds, expected transcript
    POST /tests/speech/run    {"file", "path": "batch"|"live"} -> actual+diff
    POST /tests/speech/bless  {"file", "text"} -> store as expected

The UI lives in the dashboard (StatusView.vue); the daemon serves data only.
"""
import difflib
import json
import time
import wave
from pathlib import Path

from noisy_studio import providers
from noisy_studio.config_dir import CONFIG_DIR

# A FIXED test set, not "whatever was said last": recordings live in their
# own directory, outside the utterance archive's 200-file ring - the suite
# only changes when a human adds or removes a file here. Baselines
# (expected.json) live alongside.
AUDIO_DIR = CONFIG_DIR / "speech_tests"
EXPECTATIONS_FILE = AUDIO_DIR / "expected.json"
MAX_TESTS = 20
PASS_RATIO = 0.90


def _expectations() -> dict:
    try:
        return json.loads(EXPECTATIONS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def bless(name: str, text: str) -> bool:
    path = audio_path(name)
    if path is None or not text.strip():
        return False
    data = _expectations()
    data[name] = text.strip()
    # Drop expectations whose recording is gone (the archive is a ring).
    data = {k: v for k, v in data.items() if (AUDIO_DIR / k).is_file()}
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    EXPECTATIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return True


def audio_path(name: str) -> Path | None:
    """Resolve a file STRICTLY inside the archive (no traversal)."""
    if "/" in name or "\\" in name or not name.endswith(".wav"):
        return None
    path = AUDIO_DIR / name
    return path if path.is_file() else None


def list_tests() -> dict:
    expected = _expectations()
    tests = []
    for path in sorted(AUDIO_DIR.glob("*.wav"))[:MAX_TESTS]:
        try:
            with wave.open(str(path), "rb") as w:
                seconds = w.getnframes() / w.getframerate()
        except (OSError, wave.Error):
            continue
        tests.append({"file": path.name, "seconds": round(seconds, 1),
                      "expected": expected.get(path.name, "")})
    return {"engine": providers.active_stt().label, "tests": tests}


def _transcribe_live(provider, path: Path) -> str:
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        pcm = w.readframes(w.getnframes())
    session = provider.open_stream(rate, "", lambda text: None)
    if session is None:
        return "<no streaming path>"
    frame = int(rate * 0.03) * 2
    for i in range(0, len(pcm), frame):
        session.send(pcm[i:i + frame])
        time.sleep(0.005)
    return session.finish()


def _word_diff(expected: str, actual: str) -> str:
    matcher = difflib.SequenceMatcher(
        None, expected.lower().split(), actual.lower().split())
    return " ".join(
        f"[-{' '.join(expected.split()[a1:a2])}|+{' '.join(actual.split()[b1:b2])}]"
        for op, a1, a2, b1, b2 in matcher.get_opcodes() if op != "equal")


def run_one(body: dict) -> dict:
    path = audio_path(str(body.get("file", "")))
    if path is None:
        return {"error": "unknown file"}
    mode = "live" if body.get("path") == "live" else "batch"
    provider = providers.active_stt()
    started = time.monotonic()
    try:
        actual = (_transcribe_live(provider, path) if mode == "live"
                  else provider.transcribe(path.read_bytes(), ""))
    except Exception as error:  # noqa: BLE001 - the page shows the error
        return {"file": path.name, "path": mode, "error": str(error)[:300]}
    ms = round((time.monotonic() - started) * 1000)
    expected = _expectations().get(path.name, "")
    if not expected and actual.strip():
        # First run is the baseline: the transcript becomes the expectation
        # automatically - no blessing ceremony, the icons just work.
        bless(path.name, actual)
        expected = actual
    result = {"file": path.name, "path": mode, "engine": provider.label,
              "actual": actual, "expected": expected, "ms": ms}
    if expected:
        ratio = difflib.SequenceMatcher(
            None, expected.lower(), actual.lower()).ratio()
        result["ratio"] = round(ratio, 3)
        result["ok"] = ratio >= PASS_RATIO
        if actual != expected:
            result["diff"] = _word_diff(expected, actual)
    return result
