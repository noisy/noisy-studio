# Maximum voice message length implementation plan

User-approved design: expose maximum voice message length in audio settings, default ten minutes. Reuse the existing audio control and optional dashboard visibility. Offer 1, 3, 5, 10, 15, 30 and 60 minutes; these are application safeguards, not claimed provider limits.

1. Persist max_utterance_ms in listener settings, validate 1–60 minutes, expose in status and restore on startup. Default to 600000 ms for existing installations without this setting.
2. Apply live changes through the shared segmenter in Auto and push-to-talk modes.
3. Add the audio control and verify default, live cutoff, persistence and UI emission with focused tests. Build dashboard.
4. Commit the focused change, restart dev gracefully using original data, verify runtime and push main.
