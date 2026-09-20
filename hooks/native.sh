#!/bin/sh
# Run the integration using the interpreter and dependencies inside the app.
# stdout is reserved for MCP/hook protocol output; diagnostics go to stderr.

mode="${1:-mcp}"
case "$mode" in
    mcp|hook) ;;
    *) echo "Unknown Noisy Studio integration mode." >&2; exit 1 ;;
esac

engine="${NOISY_STUDIO_ENGINE:-}"
if [ -z "$engine" ]; then
    for app in "/Applications/Noisy Studio.app" "$HOME/Applications/Noisy Studio.app"; do
        candidate="$app/Contents/Helpers/Noisy Studio Engine.app/Contents/MacOS/noisy-coding-daemon"
        if [ -x "$candidate" ]; then
            engine="$candidate"
            break
        fi
    done
fi

if [ ! -x "$engine" ]; then
    # A missing optional integration must never block a normal agent turn.
    [ "$mode" = hook ] && exit 0
    echo "Install the current Noisy Studio app in Applications, then reconnect the voice tools." >&2
    exit 1
fi

exec "$engine" --integration "$mode"
