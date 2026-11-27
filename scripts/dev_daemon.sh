#!/bin/sh
# Start a LOCAL DEV noisy-studio daemon next to the production install.
#
# Production owns ports 9765-9766 and the default config dir
# (~/.config/noisy-studio). This daemon takes the dev HTTP port below (WS
# bridge follows automatically on port+1) AND a SEPARATE config dir, so dev
# state (history, conversations, settings, voice claims) never mixes with
# production - two daemons sharing one dir fight over it, last writer wins.
# The MCP server and the hooks need no config dir here: they are dir-
# agnostic and reach the daemon by port. See docs/local-development.md. The
# dashboard is served from dashboard/dist, so it is built first when missing.
# Everything printed here and by the daemon is also saved to one log file per
# run under $DEV_CONFIG_DIR/logs; logs/latest.log points at the latest launch.
set -e

DEV_HTTP_PORT="${NOISY_STUDIO_DEV_HTTP_PORT:-7765}"
# Isolated from production on disk. Override to point elsewhere; never let it
# fall back to the default dir, or the split becomes port-only and the two
# daemons clobber each other's history.
DEV_CONFIG_DIR="${NOISY_STUDIO_DEV_CONFIG_DIR:-$HOME/.config/noisy-studio-dev}"
# Follows the config dir, so a dev instance with its own config dir keeps its
# own logs. Created only after seeding: the seed step below treats a missing
# config dir as the first run.
DEV_LOG_DIR="$DEV_CONFIG_DIR/logs"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# From here on, stdout and stderr of this script - and of the daemon, which
# inherits them through the final exec - go to the terminal AND the run log.
# POSIX sh has no process substitution, so tee reads a FIFO that becomes our
# stdout/stderr. tee ignores INT/TERM/HUP so Ctrl-C cannot cut off the
# daemon's shutdown output; it exits by itself once the daemon closes the pipe.
start_run_log() {
    mkdir -p "$DEV_LOG_DIR"
    chmod 700 "$DEV_LOG_DIR"
    RUN_LOG="$DEV_LOG_DIR/daemon-$(date +%Y%m%d-%H%M%S).log"
    ln -sfn "$(basename "$RUN_LOG")" "$DEV_LOG_DIR/latest.log"
    fifo_dir="$(mktemp -d)"
    mkfifo "$fifo_dir/log"
    (trap '' INT TERM HUP; exec tee -a "$RUN_LOG") <"$fifo_dir/log" &
    exec >"$fifo_dir/log" 2>&1
    rm -rf "$fifo_dir"
}

# First run seeds the dev dir from production: credentials, the provider
# choice AND the tuning settings (hotkeys, push-to-talk vs auto detection,
# language, batch/live modes, devices) - minus active_agent, which is per
# instance. History and conversations start empty on purpose.
SEEDED=""
if [ ! -d "$DEV_CONFIG_DIR" ]; then
    mkdir -p "$DEV_CONFIG_DIR"
    for f in credentials.json providers.json; do
        [ -f "$HOME/.config/noisy-studio/$f" ] && cp "$HOME/.config/noisy-studio/$f" "$DEV_CONFIG_DIR/$f"
    done
    if [ -f "$HOME/.config/noisy-studio/settings.json" ]; then
        python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d.pop("active_agent",None); json.dump(d,open(sys.argv[2],"w"),indent=2)' \
            "$HOME/.config/noisy-studio/settings.json" "$DEV_CONFIG_DIR/settings.json"
    fi
    SEEDED=1
fi

start_run_log

if [ -n "$SEEDED" ]; then
    echo "seeded new dev config dir $DEV_CONFIG_DIR (credentials, providers, settings)"
fi

if [ ! -f dashboard/dist/index.html ]; then
    echo "dashboard/dist missing — building the dashboard once…"
    (cd dashboard && npm install && npm run build)
fi

echo "LOCAL DEV daemon → http://127.0.0.1:${DEV_HTTP_PORT}  (config: ${DEV_CONFIG_DIR})"
echo "log: ${RUN_LOG}"
# Unbuffered: stdout is now a pipe, and Python would block-buffer it, making
# the terminal and the log lag behind the daemon.
PYTHONUNBUFFERED=1 \
NOISY_STUDIO_LISTENER_PORT="$DEV_HTTP_PORT" \
NOISY_STUDIO_CONFIG_DIR="$DEV_CONFIG_DIR" \
exec uv run noisy-studio-listener
