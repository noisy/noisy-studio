"""Agent-side entry modes of the bundled runtime, separate from audio capture."""

import os
from pathlib import Path
import sys


def run(mode: str) -> None:
    os.environ.setdefault("NOISY_STUDIO_LISTENER_PORT", "9765")
    # The desktop app owns the engine lifecycle. An MCP reconnect must never
    # create another process competing for the microphone or saved settings.
    os.environ["NOISY_STUDIO_NO_AUTOSPAWN"] = "1"
    if mode == "mcp":
        os.environ["NOISY_STUDIO_MCP_TRANSPORT"] = "stdio"
        from noisy_studio.server import main
    elif mode == "hook":
        if not getattr(sys, "frozen", False):
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
        from claude_hook import main
    else:
        raise SystemExit("Unknown Noisy Studio integration mode.")
    if mode == "mcp" and getattr(sys, "frozen", False):
        # The SDK's UTF-8 wrappers close their underlying buffers on exit.
        # Keep the original streams open for the frozen bootloader's final flush.
        original_stdin, original_stdout = sys.stdin, sys.stdout
        with os.fdopen(os.dup(original_stdin.fileno()), "r") as stdin, os.fdopen(
            os.dup(original_stdout.fileno()), "w"
        ) as stdout:
            sys.stdin, sys.stdout = stdin, stdout
            try:
                main()
            finally:
                sys.stdin, sys.stdout = original_stdin, original_stdout
    else:
        main()
