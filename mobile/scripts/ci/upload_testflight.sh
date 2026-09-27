#!/usr/bin/env bash
set -euo pipefail
# altool reads the API private key from this directory; never print its contents.
export API_PRIVATE_KEYS_DIR="$RUNNER_TEMP/noisy-mobile-signing"
cp "$API_PRIVATE_KEYS_DIR/key.p8" "$API_PRIVATE_KEYS_DIR/AuthKey_${ASC_KEY_ID}.p8"
chmod 600 "$API_PRIVATE_KEYS_DIR/AuthKey_${ASC_KEY_ID}.p8"
shopt -s nullglob
packages=(build/ios/ipa/*.ipa)
if [ "${#packages[@]}" -ne 1 ]; then
  echo "::error::Expected exactly one signed IPA to upload"
  exit 1
fi
xcrun altool --upload-app --type ios --file "${packages[0]}" \
  --apiKey "$ASC_KEY_ID" --apiIssuer "$ASC_ISSUER_ID"
