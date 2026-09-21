#!/usr/bin/env bash
# Launch a built Noisy Studio app in smoke mode and fail if it does not come
# up: main process exceptions (a missing module), an engine that never
# answers, or a version that does not match. Usage:
#   scripts/smoke.sh "<path to .app>" [expected version]
# Production apps spawn their own engine on a scratch port with a scratch
# config dir, so a running install is never disturbed. Local-mode apps
# attach to the dev daemon on 7765 and need it running.
set -euo pipefail
APP="$(cd "$(dirname "${1:?path to .app}")" && pwd)/$(basename "$1")"
EXPECTED="${2:-}"
BIN="$APP/Contents/MacOS/$(plutil -extract CFBundleExecutable raw -o - "$APP/Contents/Info.plist")"
[ -x "$BIN" ] || { echo "smoke: no executable at $BIN"; exit 1; }
PORT=$((20000 + RANDOM % 10000))
CONF="$(mktemp -d)"
trap 'rm -rf "$CONF"' EXIT
export NOISY_SMOKE=1 NOISY_SMOKE_VERSION="$EXPECTED" NOISY_APP_PORT="$PORT" NOISY_STUDIO_CONFIG_DIR="$CONF"
# Electron needs a window server; on GitHub's macOS runners it has one.
# (Not perl/timeout: a path with spaces must never pass through a shell.)
OUT="$(mktemp)"
"$BIN" >"$OUT" 2>&1 &
pid=$!
for _ in $(seq 1 150); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid" 2>/dev/null; echo "smoke: the app did not finish within 150 s"; tail -20 "$OUT"; exit 1
fi
wait "$pid" || true
line="$(grep -m1 '"smoke"' "$OUT" || true)"
if [ -z "$line" ]; then
  echo "smoke: the app printed no result (crashed before startup?)"; tail -20 "$OUT"; exit 1
fi
echo "$line"
case "$line" in *'"smoke":"ok"'*) exit 0;; *) exit 1;; esac
