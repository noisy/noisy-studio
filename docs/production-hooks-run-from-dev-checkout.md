# Production integration runs hook scripts from the mutable dev checkout

**Severity: PRE-3.0, safety.** Editing this repository can brick every
Claude Code session on the machine - including production, on a different
account and a different config dir - because they all execute hook scripts
that live in the working tree. Found live on 2026-09-10 while the hooks
were being refactored: deleting `hooks/*.py` in the checkout blocked tool
calls in the production (native app, :9765) integration and in a personal
config-dir session, not just the dev one.

## Mechanism

The native-app installer wrote `~/.claude/noisy-app/exec.sh`, registered
globally in `~/.claude/settings.json`. That script hardcodes:

    REPO="$HOME/Developer/noisy-studio"
    PY="$REPO/.venv/bin/python3"
    ... "$PY" "$REPO/hooks/$SCRIPT"

So the production hooks run **the dev checkout's** `hooks/<script>.py`
with the dev checkout's venv, against the app daemon on :9765. A missing
or erroring script exits non-zero (a missing file is exit 2), which Claude
Code treats as a tool-blocking hook result - in EVERY session whose global
settings point at this exec.sh, whatever its config dir.

**A different `NOISY_STUDIO_CONFIG_DIR` does not isolate this.** The config
dir separates the daemon's state/settings; it does not change which hook
command Claude runs. Hook isolation is per `settings.json`, and the global
one is shared.

## Why it is serious for 3.0

"Production must be stable." Today a maintainer editing their own checkout -
the normal thing to do - can silently break voice (and, because a blocking
hook stops tool calls, all agent work) for a completely separate account on
the same machine. The blast radius is every session on the box.

## Fix directions (for the native-app path)

1. The app must ship a **frozen, versioned copy** of the hooks inside the
   app bundle (or `~/.claude/noisy-app/hooks/`), and `exec.sh` must run
   THAT copy with THAT python - never `$HOME/Developer/...`. Installing =
   copying, like the plugin marketplace already does.
2. Hooks must **fail open on their own absence**: `exec.sh` already guards
   the venv (`[ -x "$PY" ] || exit 0`); it should equally guard the script
   (`[ -f "$REPO/hooks/$SCRIPT" ] || exit 0`) so a missing script never
   exits 2 and never blocks a tool. (A single defensive line would have
   prevented the whole incident.)
3. The pinned copy carries the daemon contract it matches, so a checkout
   mid-refactor cannot desync production.

## Immediate state (2026-09-10)

The legacy scripts (`post_tool_use.py`, `pre_tool_use.py`, `pre_speak.py`,
`stop.py`, `user_prompt_submit.py`, `codex.py`, `_agent_identity.py`) were
restored to their pre-overhaul content and are kept intact, so the :9765
app integration works exactly as before. The 3.0 overhaul lives in the new
`claude_hook.py` / `codex_hook.py` + `harness/` and is what new installs
register. The two coexist until the native-app install is migrated to a
frozen copy (fix #1), after which the legacy scripts can be removed.
