# Mobile redesign preview

The first scaffold used generic Material styling. This iteration ports the product
surfaces already reviewed in the desktop app instead.

| Desktop source | Flutter contract |
| --- | --- |
| `styles/tokens.css` | `design.dart`: charcoal surfaces, teal user accent, periwinkle agent accent, muted labels, 12 px borders |
| `VoiceAvatar.vue` / avatar catalog | `VoiceAvatar(voice, size)` with exact irregular frames, aspect preservation and bottom alignment |
| `VoicePersona.vue` | Talk portrait + speaking/ready/offline presentation; existing microphone and stop callbacks remain separate |
| `AgentTabs.vue` | `AgentsView(snapshot, onSelect)` shows names, harness identity, selected microphone, activity state and queued messages |
| `ConversationLog` / `AgentBubble` / `Bubble` | `MessageCard(message, onReplay?, onPause?, onSkip?, onCancel?)` retains utterance identity, role, voice, normalized status and timestamp; teal user/periwinkle agent surfaces |
| `AudioControls.vue` | Compact Auto/PTT choices + mute/stop buttons; declaration-only callbacks, no network logic in views |
| `Companion` | Portrait-first mobile composition, compact sound-location hint and recent conversation cards |

The desktop token source defines dark colors. Light previews use contrast-adjusted
teal/periwinkle and white surfaces; they do not imply a desktop light theme exists.

`python3 scripts/sync_desktop_design.py` copies original artwork, voice order,
portrait frames and crop metadata, generates `ui/avatar_catalog.dart`, and derives
status-prefix/chip tables from the desktop machine and bubble status sources. Those
canonical files. Never re-crop the sprite into equal rows/columns. This preserves
#160's geometry fix. No rendered image or metadata is invented per mobile voice.

Transport, lease ownership and confirmed routing are unchanged. `Agent.voice` and
message presentation fields are additive mappings from the existing daemon data.
The first version still controls desktop sound. Message actions are optional typed callbacks, exercised in Widgetbook and hidden
when absent in the live client. They use the desktop machine's replay/recall gates;
no new playback or voice-selection transport is claimed. Phone audio stays separate.

Review in Widgetbook: Agents 2/4/7, Talk idle/holding/speaking/muted/offline,
Recent and Settings, 360/430 widths, light/dark. Acceptance is visual; this remains
a design iteration rather than a signed mobile release.
