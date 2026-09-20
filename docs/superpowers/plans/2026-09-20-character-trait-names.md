# Consistent character traits (#108)

Use `verbosity` (0 = radio clicks, 100 = lecture) and `talkative` throughout
the daemon, API, stored characters, dashboard, reminders, demos and agent skill.
The user's existing visible values and voice behavior must stay unchanged.

Compatibility belongs at input/load boundaries: rename `chatty`, convert old
`brevity` to `100 - brevity`, and prefer explicit new keys in mixed records.
Canonical values must never be inverted again on a subsequent restart. Keep
accepting old API requests while existing dashboard windows refresh. Migrate
old cached dashboard characters at the read boundary; render canonical values
directly. Update the two affected ladders and preserve other personality traits.

- [ ] Add migration and agent-instruction regressions, then update backend
      defaults, input normalization, reminder vocabulary and saved-file load.
- [ ] Commit the verified backend change.
- [ ] Rename frontend data and presets, remove slider inversion, migrate cached
      characters, update stories and the character-matrix skill.
- [ ] Run unit/harness and frontend tests; build dashboard, Storybook and website.
- [ ] Commit, restart dev with the postponable 60-second countdown and verify
      canonical live values and on-disk migration without exposing session data.

Work starts from the #107 fixes already running on dev. Publishing this issue's
changes is separate from the authorized push and closure of #107.
