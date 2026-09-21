> Historical research: browser audio transport was removed in V3. The WebSocket now serves dashboard state only; use the native microphone path for current audio testing.

# Research: automated end-to-end testing with voice, no human in the loop

Status: research / proposal. Nothing implemented yet.

## Problem

Most bugs we find are found by Krzysztof talking to a live instance. That
means:

- a bug only exists once someone speaks into a microphone,
- reproduction depends on timing (barge-in, VAD boundaries, playback
  overlap), which a human cannot repeat twice the same way,
- error paths (STT failure, TTS 429, tab lease lost mid-utterance) are
  almost never exercised, because provoking them by hand is tedious,
- the current suite is `tests/unit/*` only: good coverage of pure helpers,
  zero coverage of "an utterance travels through the whole system".

Goal: a test tier where a scripted "user" speaks, the system runs for real,
and assertions run on what came out - transcripts, dashboard state, spoken
audio - with no human present.

## What the architecture already gives us

Reading `src/noisy_studio/`, there are four natural seams. This is the most
important finding: we do not need microphones or speakers to drive the
system end to end.

1. **WS `:8766` tab-audio bridge** (`listener/tab_audio.py`). The browser
   tab is already a *replaceable* audio device. Protocol is small: text
   JSON `hello` / `hb` in, binary PCM16 frames in, `play` / `stop` JSON out
   followed by audio out. Anything that speaks this protocol is a valid
   mic+speaker. A test client is ~80 lines with the `websockets` dep we
   already ship.
2. **HTTP `:8765`** (`listener/http_api.py`, ~35 endpoints): `/speak`,
   `/drain`, `/status`, `/activity`, `/events`, `/interrupt`, `/ptt`,
   `/mute`, `/character`, `/mode`. This is the full observable surface, so
   assertions do not need to scrape the UI.
3. **Hooks** (`hooks/*.py`) are ordinary scripts that poll `/drain`. They
   can be invoked directly with a fake Claude Code payload on stdin.
4. **STT/TTS are single-function HTTP clients** (`listener/stt.py`,
   `tts.py`) going through `httpx` to `api.x.ai`. `respx` is already a dev
   dependency, so the provider is interceptable without touching prod code.
   Caveat: `XAI_API_BASE` is a module constant, not an env var - making it
   configurable is a one-line prerequisite for the fake-provider options.

## Assumptions

These drive every option below. If one is wrong, re-score the options.

- A1. A test must be runnable in CI: headless, no audio hardware, no
  browser, deterministic enough to gate a merge.
- A2. Real Grok API calls are CHEAP and cost is not a design constraint:
  per `listener/pricing.py`, STT is $0.10/audio-hour and TTS $4.20/M chars,
  so a ~30-scenario suite is ~$0.07 a run, and `audio_cache.py` already
  serves repeated identical TTS for free. What makes live calls unfit for a
  merge gate is NON-DETERMINISM (ASR output drifts run to run), plus rate
  limits and API-key handling in forks.
- A3. The bugs we actually care about are **orchestration** bugs -
  ordering, state, concurrency, lease ownership, error recovery - not
  "did the ASR hear the word correctly". ASR accuracy is the vendor's
  problem.
- A4. Wall-clock timing is a first-class part of the behaviour (barge-in,
  debounce, unheard-parking), so a fake clock or time scaling is needed
  for tests to be fast AND stable.
- A5. We can add small, non-invasive seams to prod code (env-configurable
  API base, an injectable clock, a test-only WS client). We are not going
  to restructure the daemon to be testable.

## Options

### Option A - Live loopback: real audio devices, real API

Virtual audio cables (BlackHole on macOS), a script that plays WAVs into
the input device and records the output device, real Grok STT/TTS.

- Pro: tests literally what the user experiences, including the audio
  hardware layer and vendor quirks.
- Con, in order of severity: **CI runners have no audio hardware** and
  cannot load a kernel-level audio driver, so this can never gate a PR
  (A1) - fatal on its own. Then non-deterministic ASR output forces fuzzy
  assertions on a slow test, which is how suites get ignored. Then
  machine-specific BlackHole setup. Cost is NOT an objection (A2).
- Note: the fatal objection is about *hardware*, not about the API. It
  rules out Option A only; it says nothing against Option B.
- Verdict: **not the main tier.** Worth keeping as a rare manual/nightly
  canary on Krzysztof's machine only.

### Option B - Fake tab client + real Grok API

A synthetic WS client on `:8766` replaces the browser tab. It pushes
pre-recorded PCM into the bridge; the daemon does real VAD, real STT,
real TTS; the client captures the audio the daemon plays back.

- Pro: no hardware, exercises the entire real pipeline including VAD, still
  reasonably simple to build.
- Con: non-deterministic (A2, A3), so it cannot gate a merge - test
  failures will sometimes be vendor hiccups, which is exactly the kind of
  noise that makes people ignore a suite. Rate limits under a parallel
  suite are a real risk; spend is not (~$0.07/run).
- Verdict: **yes, but as a nightly job**, not on every PR.

### Option C - Fake tab client + recorded provider (cassettes)

Same harness as B, but STT and TTS responses come from recorded fixtures
(`respx` interception, or a tiny local HTTP server pointed at by
`XAI_API_BASE`). Record once against the real API, replay forever.

- Pro: deterministic, fast, CI-safe (the win is repeatability and no
  vendor dependency, not the saved cents). Keeps the real VAD, real queue,
  real state machine, real playback path - which is where the bugs live
  (A3). Error injection is trivial: a cassette can return 429, a truncated
  body, a 30 s hang, garbage JSON.
- Con: cassettes drift when the vendor changes response shape - needs a
  periodic re-record (which Option B covers). Does not validate ASR
  accuracy, by design.
- Verdict: **this is the recommended core tier.**

### Option D - Text-level E2E: skip audio, drive HTTP + hooks

No WS, no audio. Inject transcripts at the queue boundary, call `/speak`,
run the real hook scripts, assert on `/drain`, `/status`, `/activity`.

- Pro: cheapest and fastest of all (milliseconds), trivially deterministic,
  covers the biggest bug class: agent registration, mute, interrupt,
  unheard parking, multi-agent ordering, hook contract.
- Con: blind to VAD, rechunking, lease election, playback overlap - the
  audio-timing bugs that are hardest to reproduce by hand.
- Verdict: **yes, as the base tier.** Complementary to C, not a rival. It
  should be written first because it is cheap and catches a lot.

### Option E - Offline local STT/TTS instead of cassettes

Swap Grok for whisper.cpp + Piper behind the same interface.

- Pro: offline, and unlike cassettes it accepts *arbitrary* new audio
  without a re-record, so new scenarios cost nothing.
- Con: a second, heavy toolchain in CI; different accuracy profile means
  assertions must be fuzzy; it tests *a* speech stack, not *our* speech
  stack.
- Verdict: **no for CI.** Possibly useful later for fuzz-style scenario
  generation.

### Option F - Agent-driven "user simulator"

An LLM agent plays the user: decides what to say next based on what it
heard, TTS-es it into the bridge.

- Pro: explores conversational paths nobody scripted; good bug *finder*.
- Con: non-deterministic by construction, so it can never be a regression
  gate; needs a judge to decide pass/fail. LLM tokens, not voice credits,
  are the cost here.
- Verdict: **not a test suite.** Interesting later as a nightly
  exploratory/chaos run that files issues rather than failing builds.

## Recommendation: three tiers

| Tier | What | When | Determinism |
|---|---|---|---|
| 1 | Option D - HTTP + hooks contract E2E | every PR | full |
| 2 | Option C - fake tab + cassettes, real VAD/state | every PR | full |
| 3 | Option B - fake tab + live API | nightly | best effort |

Option A stays a manual smoke check (extend `scripts/smoke_test.py`).
Option F is a future experiment, decoupled from CI.

## What makes tiers 1-2 actually work

- **Scenario DSL.** A test should read like a timeline, not like socket
  code: `speak_wav("hello.wav") -> expect_transcript(contains="hello") ->
  agent_says("...") -> at(+0.4s) speak_wav("stop.wav") ->
  expect_playback_stopped()`. Without this, nobody writes the second test.
- **Injectable clock.** Barge-in and debounce windows must be simulated,
  not slept through (A4). This is the single biggest prerequisite in prod
  code.
- **Fixture corpus.** A dozen short WAVs recorded once: short utterance,
  long utterance, silence, background noise, overlapping speech, a
  garbled one-word artifact.
- **Error catalogue as first-class scenarios.** STT 500, STT empty string,
  TTS 429, TTS truncated audio, tab lease stolen mid-playback, tab
  disconnect mid-utterance, daemon restart with a queued utterance.
- **One assertion surface.** Prefer `/events` and `/status` snapshots over
  poking internals, so tests survive refactors.

## Prerequisites in prod code (small)

1. Make `XAI_API_BASE` env-overridable (`tts.py:10`).
2. Introduce an injectable time source used by the speech/state machines.
3. Extract a reusable test WS client for the `:8766` protocol.
4. Add a `tests/e2e/` package with a daemon-on-a-random-port fixture.

## Open questions for Krzysztof

- Are audio-timing bugs (barge-in, lease, overlap) actually the painful
  ones, or is it mostly agent/dashboard state? That decides whether tier 2
  is worth building before tier 1 pays off.
- Which machine runs the nightly live tier? (Spend is a non-issue at
  ~$0.07/run; the constraint is a box with the key and, for tier A, audio
  hardware.)
- Do we want dashboard UI coverage at all, or is the HTTP surface enough?
