# Noisy Studio mobile preview

Flutter companion for the desktop daemon, issue #170. Android ID:
`pl.noisy.noisy_studio_mobile`; iOS ID: `pl.noisy.noisyStudioMobile`.

**Audio is captured and played on the desktop.** This app selects the receiving
agent and operates the desktop microphone. It never requests phone microphone
permission. Phone audio transport and pairing belong to #124. Pairing is honestly
shown as unavailable. Do not expose the unauthenticated daemon to the Internet.

## Develop and review

Flutter 3.47.5 / Dart 3.13.4; Java 17 for Android.

```sh
cd mobile
flutter pub get
scripts/check.sh
flutter run                              # fixture mode by default
flutter run -d chrome -t widgetbook/main.dart
flutter build apk --debug
# Read-only single-origin HTTP contract check (never starts recording):
dart run tool/check_connection.dart http://127.0.0.1:7765
```

Widgetbook includes 0/2/4/7 agents, idle/holding/speaking/muted/offline Talk,
Recent and Settings, two phone sizes and light/dark themes. It uses the same views
as the app. Portraits reuse the desktop editorial artwork and irregular crop metadata.
See `DESIGN.md` for the desktop component/interaction mapping and sync command. Roboto is bundled locally with its license; no runtime font downloads.

Settings accepts an HTTP(S) origin, remembers only its address, and connects only
on request. The daemon must already be reachable. This app never changes its bind
address. HTTP uses `/status`, `/utterances`, `/active-agent`, `/ptt`, `/mute`,
`/interrupt`, `/settings`. State refreshes once per second after the previous HTTP snapshot completes.
Both reads and commands use exactly the supplied HTTP(S) origin; no second port
or WebSocket proxy route is required. Each snapshot reads `/status` and
`/utterances`; polling stops on failure, cancellation or disconnect. Reconnecting
is explicit and never restarts push-to-talk.
No phone microphone audio or pairing code is sent. An HTTPS proxy can provide transport encryption, but HTTPS alone is not
authentication. Public deployment still requires the authenticated remote boundary
tracked in #124; this app does not create a tunnel or implement proxy login.
HTTP 401/403 explains that this client needs authenticated access.
Local HTTP is permitted by both
platform manifests for this preview. Web preview requires the daemon's CORS policy
to allow its origin; native builds do not use browser CORS.

Agent selection is serialized and Talk controls remain disabled until the latest
server confirmation. Disconnecting or switching to demo invalidates old routing
completions. The confirmed identity, including aliases or no active conversation,
is authoritative.

PTT renews every 500 ms after the previous acknowledgement. Release waits for an
in-flight renewal. Backgrounding, navigation, routing changes, Auto mode, muting,
disconnection and disposal cancel the local hold. Network loss disables controls;
reconnect is explicit, and never resumes a hold. The daemon's existing lease
expiry is the final fallback if a release cannot reach it. This preview uses the
existing global lease; it cannot arbitrate simultaneous desktop/mobile holds.
Pending-message badges are labeled queued, not falsely described as read receipts.

## CI and signing handoff

`.github/workflows/mobile.yml` checks, builds a **debug-signed preview APK**, app
web preview and Widgetbook for scoped pushes/PRs. These are seven-day artifacts,
not releases. Android preview requires no secrets. Stable Android release signing
is deliberately not implied by a debug build and will need a separate app key
before distribution.

The manual-only `.github/workflows/mobile-ios.yml` archives and cloud-signs an IPA;
it **never submits to a store or TestFlight**. In `noisy/noisy-studio`, create the
`mobile-ios` environment with these secret names (never paste their values into
issues/chat):

- `ASC_KEY_ID`
- `ASC_ISSUER_ID`
- `ASC_KEY_P8_BASE64`
- `APPLE_TEAM_ID`

Register `pl.noisy.noisyStudioMobile` and a distinct Noisy Studio Mobile App Store
Connect record on the authorized Apple team. The API key needs cloud signing and
provisioning permissions, as in Bucky. Configure environment protection if desired.
Do not reuse Bucky's bundle ID, app record, entitlements, Firebase files or Android
certificate fingerprint. The signing key is removed even on failure. Missing
secrets do not block fixtures, tests, Android or web previews.

Implementation is original. Bucky shell d66d763 and its CI were inspected with the
owner's authorization as reference for organization, pinned setup action, Java 17,
cloud signing and manual iOS budgeting; no private product code/assets were copied.
The monorepo keeps daemon contracts and mobile changes reviewable together.
