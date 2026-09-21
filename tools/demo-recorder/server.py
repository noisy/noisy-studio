"""Local-only authoring tool; never starts or configures the voice daemon."""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from websockets.sync.server import serve

from noisy_studio.listener.stt_stream import StreamingSession

ROOT = Path(__file__).resolve().parent
CLIPS = ROOT.parent.parent / "dashboard/src/components/marketing/crew-voice"
ASSETS = {
    "/clips/hero-lux-search-production.mp3": (ROOT / "clips/hero-lux-search-production.mp3", "audio/mpeg"),
    "/": (ROOT / "index.html", "text/html"),
    "/audio-editor": (ROOT / "audio-editor.html", "text/html"),
    **{f"/{name}": (ROOT / name, mime) for name, mime in [
        ("audio-editor.mjs", "text/javascript"),
        ("audio-edits.mjs", "text/javascript"),
        ("audio-editor.css", "text/css"),
        ("recorder.mjs", "text/javascript"),
        ("timeline.mjs", "text/javascript"),
        ("scenarios.mjs", "text/javascript"),
        ("pcm-worklet.js", "text/javascript"),
        ("style.css", "text/css"),
    ]},
    **{f"/clips/{name}.mp3": (CLIPS / f"{name}.mp3", "audio/mpeg")
       for name in ("lux-1", "lux-2", "rex-1", "luna-1", "luna-2")},
    **{f"/clips/hero-lux-{index}.mp3": (ROOT / "clips" / f"hero-lux-{index}.mp3", "audio/mpeg")
       for index in range(1, 5)},
    **{f"/clips/hero-lux-search-{index}.mp3": (ROOT / "clips" / f"hero-lux-search-{index}.mp3", "audio/mpeg")
       for index in range(1, 6)},
}


def transcribe_connection(socket, session_factory=StreamingSession):
    session = None
    utterance = None

    def emit(kind, **fields):
        socket.send(json.dumps({"type": kind, **fields}))

    try:
        for message in socket:
            if isinstance(message, bytes):
                if session is not None:
                    session.send(message)
                continue
            command = json.loads(message)
            if command["type"] == "start":
                if session is not None:
                    raise ValueError("Previous utterance is still open")
                utterance = str(command["utterance"])
                rate = int(command["sampleRate"])
                if rate not in (16000, 22050, 24000, 32000, 44100, 48000, 96000):
                    raise ValueError("Unsupported sample rate")
                session = session_factory(
                    rate, "en",
                    lambda text, identity=utterance: emit(
                        "transcript", utterance=identity, text=text, final=False),
                )
                emit("ready", utterance=utterance)
            elif command["type"] == "finish" and session is not None:
                text = session.finish()
                session = None
                emit("transcript", utterance=utterance, text=text, final=True)
            elif command["type"] == "abort":
                break
    except Exception:
        # Provider exception messages can contain credential-bearing HTTP data.
        # Keep this local tool's browser/log output deliberately credential-free.
        try:
            emit("error", message="Transcription disconnected. Check the local STT credentials and connection; save this take before retrying.")
        except Exception:
            pass
    finally:
        if session is not None:
            session.abort()


def make_handler(ws_port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/config.json":
                content = json.dumps({"websocketPort": ws_port}).encode()
                mime = "application/json"
            elif path in ASSETS:
                file, mime = ASSETS[path]
                content = file.read_bytes()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    with serve(
        transcribe_connection, "127.0.0.1", args.port + 1,
        origins=[f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"],
        max_size=262144,
    ) as websocket_server:
        threading.Thread(target=websocket_server.serve_forever, daemon=True).start()
        with ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.port + 1)) as http:
            print(f"Recorder: http://127.0.0.1:{args.port} — camera/mic stay off until you click Record", flush=True)
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
