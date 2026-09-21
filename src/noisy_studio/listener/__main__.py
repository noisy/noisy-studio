"""Entry point for the frozen daemon.

A console_script cannot be frozen - PyInstaller needs a real module to
start from. `python -m noisy_studio.listener` works the same way, so this
serves both the frozen binary and anyone who prefers it to the script.
"""

import sys


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--integration":
        from noisy_studio.integration import run

        run(sys.argv[2])
        return
    from noisy_studio.listener.daemon import main as run_daemon

    run_daemon()

if __name__ == "__main__":
    main()
