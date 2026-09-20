"""MCP server that lets the assistant speak to the user via Grok Voice.

Thin messenger: all rendering, playback, queueing and turn-taking live in
the listener daemon (the single owner of mic and speakers). This server
just forwards speak/announce requests over localhost HTTP — so a stale
server process left behind by an MCP reconnect can't talk over anyone.
"""

import asyncio
import os
import socket
import subprocess
import sys
import time

import httpx
from mcp.server.fastmcp import FastMCP


LISTENER_PORT_ENV_VAR = "NOISY_CODING_LISTENER_PORT"
# speak blocks until the daemon has waited out the user's turn, rendered
# AND played the utterance — allow for a long queue ahead of us.
SPEAK_TIMEOUT_SECONDS = 180.0
DAEMON_DOWN_MESSAGE = (
    "The voice daemon is not reachable, so nothing was spoken. "
    "Deliver the message in writing instead."
)

mcp = FastMCP("noisy-coding")


async def _identity_error(agent_id: str | None) -> str | None:
    """Speech identity is supplied by the trusted host hook, on every harness.

    The hook's PreToolUse rewrites `agent_id` on every speak/announce/
    change_voice call to the conversation it belongs to; the server never
    guesses it from cwd or process environment (that guessing is what made
    two sessions in one directory steal each other's voice). A call that
    arrives without it means the hook did not run: fail closed.
    """
    if agent_id and agent_id.strip():
        return None
    message = (
        "Voice session identity is missing: the noisy-coding PreToolUse hook did not run "
        "for this call. Check that the hooks are registered (/hooks) and that this session "
        "started after they were installed; a restart of the session usually fixes it."
    )
    port = os.environ.get(LISTENER_PORT_ENV_VAR, "8765")
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            await client.post(f"http://127.0.0.1:{port}/event", json={"kind": "voice_identity_error", "detail": message})
    except httpx.HTTPError:
        pass
    return message


async def _daemon_speak(body: dict, agent_id: str | None = None) -> dict | None:
    """POST /speak to the daemon; None when it's unreachable (fail open).

    A daemon that is merely starting up must not turn speak into an
    exception — on the first failure we (re)spawn it and retry once.
    """
    error = await _identity_error(agent_id)
    if error:
        return {"error": error}
    port = os.environ.get(LISTENER_PORT_ENV_VAR, "8765")
    body = dict(body)
    body["agent"] = agent_id.strip()
    timeout = httpx.Timeout(SPEAK_TIMEOUT_SECONDS, connect=2.0)
    for attempt in (0, 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"http://127.0.0.1:{port}/speak", json=body
                )
                return response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == 0:
                await asyncio.to_thread(_ensure_daemon)
    return None


def _speak_result_message(result: dict | None) -> str | None:
    """Shared failure reporting for speak/announce; None means success."""
    if result is None:
        return DAEMON_DOWN_MESSAGE
    if "error" in result:
        return f"Speech failed: {result['error']}"
    return None


@mcp.tool()
async def speak(text: str, interrupt: bool = False, speaker: str = "", agent_id: str | None = None) -> str:
    """Speak a short message aloud to the user through their speakers.

    Use this to deliver a spoken TL;DR alongside (not instead of) your written
    answer: 1-3 conversational sentences summarizing the outcome, a finding,
    or a question. Never read code, file paths, or long explanations aloud.

    You send only the text: voice, speed and language belong to the daemon
    (the user controls them on the dashboard). To deliberately switch your
    voice, call change_voice.

    Concurrent speech is serialized: by default a new call WAITS for the
    current utterance to finish (queued), and for the user to finish
    speaking. Set interrupt=True to cut the current utterance off and speak
    immediately — use it only when your previous words are now stale (e.g.
    the user corrected you mid-answer).

    Args:
        text: What to say. Plain conversational prose. Mark the key words the
            listener must catch with markdown bold (**like this**) — they get
            vocal emphasis and show bold on the live dashboard. Also supports
            inline speech tags like [pause] or [laugh] and wrapping tags like
            <soft>text</soft>.
        interrupt: Cut off any utterance currently playing and speak now.
        speaker: ONLY for subagents. If you are a subagent (Task/Agent tool),
            pass your role name here (e.g. "researcher") — the dashboard
            shows the message under that name with its own portrait, and the
            daemon gives you a stable voice distinct from the main agent's.
            The main agent must leave this empty.
        agent_id: Integration-supplied conversation identity. Leave unset;
            the trusted host hook supplies it when required.
    """
    body: dict = {"text": text, "interrupt": interrupt, "wait": True}
    if speaker.strip():
        body["speaker"] = speaker.strip()
    result = await _daemon_speak(body, agent_id)
    failure = _speak_result_message(result)
    if failure:
        return failure
    return f"Spoke the message aloud with voice '{result.get('voice', '?')}'."


@mcp.tool()
async def announce(text: str, agent_id: str | None = None) -> str:
    """Speak a quick spoken update WITHOUT waiting for it to finish.

    Fire-and-forget: use this to tell the user what you just did and keep
    working ("done with X, moving on") — it returns immediately and plays in
    the background, queued behind any current speech. Use `speak` instead when
    you are asking a question or otherwise waiting for the user's reply.
    Like speak, it carries only text — voice/speed/language live in the daemon.
    """
    result = await _daemon_speak({"text": text, "wait": False}, agent_id)
    failure = _speak_result_message(result)
    if failure:
        return failure
    return "Announcement queued; playing in the background."


@mcp.tool()
async def change_voice(voice_id: str, speaker: str = "", agent_id: str | None = None) -> str:
    """Deliberately switch this agent's speaking voice from now on.

    Updates your character in the listener daemon: the dashboard shows the
    new voice and every later speak/announce uses it (it also persists
    across restarts). Use list_voices to see the options. Speak itself
    carries no voice information — this call is the only way to change how
    you sound, so use it consciously (e.g. when the user asks for it).

    Args:
        voice_id: Which voice to switch to.
        speaker: Move a named SPEAKER's voice instead of your own — the
            personas you address with speak(speaker=...). A voice already
            held by someone else is refused rather than duplicated, so two
            speakers never become indistinguishable by ear.
    """
    error = await _identity_error(agent_id)
    if error:
        return error
    port = os.environ.get(LISTENER_PORT_ENV_VAR, "8765")
    body: dict = {"voice_id": voice_id}
    if speaker.strip():
        body["speaker"] = speaker.strip()
    body["agent"] = agent_id.strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(f"http://127.0.0.1:{port}/voice", json=body)
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return "The voice daemon is not reachable; your voice is unchanged."
    if "error" in data:
        return f"Voice change failed: {data['error']}"
    return f"Voice changed to '{data['voice']}' for all your future speech."


@mcp.tool()
async def set_speaker_style(speaker: str, color: str = "", label: str = "") -> str:
    """Style a named speaker's bubbles: palette color and/or a free title.

    Color is a FIXED palette, persisted across restarts:
      - "normal"  the main agent's own look (e.g. a chat moderator persona)
      - "green"   the guest look (plain subagent personas - also the fallback)
      - "purple"  Twitch chat viewers
      - "red"     YouTube chat viewers
      - "default" clear the entry, back to guest green

    The label is FREE TEXT shown as the bubble's title instead of the
    standard "<SPEAKER> · AGENT" - e.g. "YouTube · someRandomGuy" or
    "Luna - chat agent". Empty label leaves the current one; to clear a
    label set it to "-".

    Use it once per speaker (e.g. a viewer's first message); repeating it
    is harmless.

    Args:
        speaker: The speaker name (same as in speak(speaker=...)).
        color: One of default/normal/green/purple/red, or "" to leave as is.
        label: The bubble title to show, "" to leave as is, "-" to clear.
    """
    port = os.environ.get(LISTENER_PORT_ENV_VAR, "8765")
    body: dict = {"speaker": speaker.strip()}
    if color.strip():
        body["color"] = color.strip().lower()
    if label.strip():
        body["label"] = "" if label.strip() == "-" else label.strip()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://127.0.0.1:{port}/speaker-style", json=body
            )
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return "The voice daemon is not reachable; nothing changed."
    if "error" in data:
        return f"Style change failed: {data['error']}"
    parts = []
    if data.get("color"):
        parts.append(f"color {data['color']}")
    if "label" in body:
        parts.append(f"title {body['label'] or 'cleared'!r}")
    return f"Bubbles for '{data['speaker']}': " + (", ".join(parts) or "unchanged") + "."


@mcp.tool()
async def list_voices() -> list[dict]:
    """List the TTS voices the active provider offers for the speak tool."""
    from noisy_coding import providers

    return await providers.active_tts().list_voices()


def _daemon_running(port: int) -> bool:
    """True if something is already listening on the daemon's port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _ensure_daemon() -> None:
    """Adopt a running listener daemon, or spawn one as a child process.

    Daily use: the server spawns the daemon so voice "just works" with no
    manual step. Development: start the daemon yourself first — the server
    sees the port taken, adopts it, and you keep restarting the daemon in
    place without touching the server. Set NOISY_CODING_NO_AUTOSPAWN=1 to opt
    out (e.g. to always manage the daemon by hand).
    """
    if os.environ.get("NOISY_CODING_NO_AUTOSPAWN"):
        return
    port = int(os.environ.get(LISTENER_PORT_ENV_VAR, "8765"))
    if _daemon_running(port):
        return  # adopt the existing daemon
    try:
        # Child process: dies with the server (no orphaned daemons). A dev
        # daemon started by hand is a separate process and outlives us.
        subprocess.Popen(
            [sys.executable, "-m", "noisy_coding.listener.daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):  # wait up to ~2s for it to come up
            if _daemon_running(port):
                break
            time.sleep(0.1)
    except OSError:
        pass  # fail open: speak still works, just no listening


def main() -> None:
    _ensure_daemon()
    # stdio (default): Claude Code launches this process per session.
    # http: optional standalone source transport — a client connects
    # with `claude mcp add --transport http http://host:8767/mcp`.
    if os.environ.get("NOISY_CODING_MCP_TRANSPORT", "stdio") == "http":
        mcp.settings.host = os.environ.get("NOISY_CODING_MCP_BIND", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("NOISY_CODING_MCP_PORT", "8767"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
