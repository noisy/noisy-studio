# Microphone timeline fixes (#134, #135)

Approved issue requirements: keep device changes useful without showing pre-conversation history or repeated reopen noise.

- [x] Expose conversation creation time and filter system rows in one dashboard helper, shared by the composable and Storybook examples. Older daemons fall back to the first own utterance, with no system rows before an unknown start. Keep own speech untouched. Cover both older and newer conversations.
- [x] Separate opening/fallback from microphone timeline reporting. Record the final effective device once per attempt. Persist the last effective device in a dedicated config file (avoid races with settings writes), suppress same-device reopens/restarts, and compact a repeated transition within five seconds. Test fallback/recovery, watchdog reopen, restart, and short flapping sequences with synthetic devices.
- [x] Build/check dashboard and relevant daemon behavior; review Storybook examples; commit each issue locally on main. Use a postponable restart for the dev daemon and verify its microphone. Do not push.

Dev rollout: restarted gracefully on 7765 with the dev configuration and Jabra Link 380. Verified the effective device was saved, conversation creation times are present in status, and the current dashboard is served. Storybook examples cover new/existing conversation timelines and compacted reconnect counts. Changes remain local on main.
