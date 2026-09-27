# Talk-first mobile integration and release

**Goal:** Ship the user-approved portrait crew, Recent replies and compact agent detail in the existing native mobile companion, then upload a signed iOS build to TestFlight.

**Architecture:** Extract the approved reusable UI from the isolated mobile prototype into production widgets. Keep daemon access and recording lifecycle in the existing core layer; introduce a focused direct-hold coordinator if necessary to serialize recipient selection, mode changes and lease cleanup. Widgetbook must render the same production components after integration.

**Stack:** Flutter 3.47.5, Dart 3.13.4; current HTTP daemon contract and GitHub Actions signing workflow.

## Constraints

- Existing mobile transport controls desktop audio. Phone microphone transport and remote authentication are separate work, not silently implemented by this release.
- Crew portraits touch tile top/side edges, use one outer shape and show only conversation titles; recording uses a microphone badge.
- Tap opens details; hold records to that conversation. Recent combines all messages; held Reply targets the message author. Auto selection is explicit and never changes when messages arrive.
- Cancel slides out behind portraits/detail controls and left from Reply in 180 ms, respecting reduced motion. Hover is reversible; only release over visible Cancel discards. System interruption cancels safely.
- Detail Cancel matches the talk control width and reaches the bottom. Navigation keeps its space but is hidden during detail holds and disabled during any hold.
- Mode switch reads Push to talk / Auto. Preserve connection settings, offline feedback, replay/pause/skip and message recall.
- Never change stream configuration for testing. A required daemon contract update uses the graceful restart countdown and preserves the existing config. Never print signing credentials.

## 1. Production UI and recording coordination

Files: mobile/lib/main.dart, mobile/lib/core/ptt_lease.dart, mobile/lib/core/agent_selection.dart, mobile/lib/ui/screens.dart, new focused UI/hold files as needed, mobile/widgetbook/talk_first.dart.

- [x] Reconcile the prototype branch with current main, preserving unrelated changes.
- [x] Extract the approved hold gesture and cancellation sheets into reusable production widgets. Replace synthetic callbacks with explicit asynchronous start/finish callbacks; disable controls while routing is pending or disconnected.
- [x] Wire crew/detail/Recent to Snapshot and confirmed conversation identities. Maintain separate detail navigation and selected Auto recipient.
- [x] Serialize direct hold: suspend Auto through /settings if needed, await /active-agent confirmation, then acquire /ptt. If release or cancellation happens while a request is pending, do not start a late recording.
- [x] Distinguish send from discard. Discard calls /abort-recording before /ptt release. Stop lease renewal first and await any pending renewal. Restore the prior confirmed Auto recipient/mode only after cleanup; do not restore stale state after disconnect or an intervening user action.
- [x] Make backgrounding, navigation, connection loss and disposal terminate owned recording safely. Keep command failures visible and prevent automatic recording on reconnect.
- [x] Keep Widgetbook production-backed and retain the approved static held-state examples.
- [x] Commit coherent UI and coordinator changes independently after their relevant checks pass.

## 2. Validation and review

Files: mobile/test/ptt_lease_test.dart, mobile/test/agent_selection_test.dart, focused hold/controller/widget tests; existing mobile test suite.

- [x] Test request ordering: selection acknowledgement before recording, abort before release, release while start is pending, direct reply from Auto and restoration, lifecycle interruption and failed commands.
- [x] Test gesture routing at its boundary: quick tap versus hold/scroll, release on visible Cancel versus moving back, partial animation hit region, transformed/scaled layout and detail navigation restoration.
- [x] Test production app callbacks against a fake daemon boundary without repeating HTTP mechanics already covered by daemon_client_test.dart.
- [x] Run mobile/scripts/check.sh, prototype gesture tests if outside test/, and flutter build web. Review real production screens in a local browser with fixture data and use read-only daemon connection checks.
- [x] Review the resulting diff against approved interactions; fix issues before merging.

## 3. Release

Files: mobile/pubspec.yaml, release notes/documentation as needed; existing .github/workflows/mobile-ios.yml and mobile.yml.

- [x] Verify previous iOS upload succeeded and signing secret names exist without reading their values.
- [x] Advance the mobile prerelease version coherently; GitHub run number supplies the increasing iOS build number.
- [ ] Merge reviewed mobile branch to main, rerun checks on the combined tree, commit release metadata and push main.
- [ ] Trigger mobile-ios.yml on main with upload_testflight=true. Monitor archive/export/upload to completion; diagnose failures without exposing secrets.
- [ ] Verify Android preview CI separately. Do not represent debug APK artifacts as a signed Play Store release.
- [ ] Report exact version/build, upload outcome and any Apple processing/tester-availability limitation. Do not claim public App Store publication.

Validation: 499 isolated-config Python unit tests, 43 mobile tests, 16 shared gesture tests, clean Flutter analyzer and successful production/Widgetbook web builds. Production offline, portrait crew, Recent and detail screens inspected at 390×844 with demo data. The mobile branch was fast-forwarded to main, preserving the exact tested combined tree.
