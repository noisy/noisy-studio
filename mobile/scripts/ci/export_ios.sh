#!/usr/bin/env bash
set -euo pipefail
key_path="$RUNNER_TEMP/noisy-mobile-signing/key.p8"
xcodebuild archive -workspace ios/Runner.xcworkspace -scheme Runner \
  -configuration Release -destination 'generic/platform=iOS' \
  -archivePath build/ios/Runner.xcarchive CODE_SIGNING_ALLOWED=NO \
  DEVELOPMENT_TEAM="$APPLE_TEAM_ID"
# Remove ad-hoc framework signatures so export signs using the proper identities.
for framework in build/ios/Runner.xcarchive/Products/Applications/Runner.app/Frameworks/*.framework; do
  executable="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$framework/Info.plist")"
  codesign --remove-signature "$framework/$executable" || true
  rm -rf "$framework/_CodeSignature"
done
python3 - <<'PY'
import os, plistlib
with open('build/ios/ExportOptions.plist', 'wb') as target:
    plistlib.dump({'method': 'app-store-connect', 'destination': 'export',
                  'signingStyle': 'automatic', 'teamID': os.environ['APPLE_TEAM_ID'],
                  'manageAppVersionAndBuildNumber': False}, target)
PY
xcodebuild -exportArchive -archivePath build/ios/Runner.xcarchive \
  -exportOptionsPlist build/ios/ExportOptions.plist -exportPath build/ios/ipa \
  -allowProvisioningUpdates -authenticationKeyPath "$key_path" \
  -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID"
