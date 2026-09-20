# Path-free conversation labels (#107)

Goal: a filesystem path must never appear in a conversation tab, companion
title or tooltip, or browser tab title. Keep routing identities unchanged.

The earlier identity migration only recognizes transcript filenames. Titles
from hooks, legacy registration, and saved conversations still accept paths;
the companion and browser title also fall back to raw keys.

Use the existing “New conversation” placeholder when no safe title exists.
Conservatively reject titles containing either directory separator or a Windows
drive prefix, including paths embedded in prose. This deliberately also rejects
slash-containing titles such as “CI/CD”: guessing whether a slash denotes a
directory cannot guarantee the requested privacy rule. Keep the last safe title
when a later event supplies an unsafe one. Do not shorten paths to basenames or
change identity/routing as part of this fix.

The backend guards saved and incoming titles and legacy display metadata. The
frontend guards the actual rendering boundaries as well, so an older daemon
cannot expose a path during an upgrade. Tests belong at the shared policy and
these distinct boundaries, without repeating every policy case per consumer.

- [ ] Reproduce unsafe saved titles, lifecycle updates and legacy metadata.
- [ ] Guard backend titles and labels; verify focused Python tests.
- [ ] Guard dashboard, companion and browser titles; add regression stories.
- [ ] Run unit/harness tests, frontend tests and dashboard build; commit.
- [ ] Schedule the dev restart with a 60-second countdown; wait for the old
      port to close, start the dev script, and verify the Jabra microphone.
- [ ] Check sanitized live status fields and the daemon-served UI without
      printing real session names or paths.
