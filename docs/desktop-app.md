# Native desktop application

The supported release is Noisy Studio for macOS Apple Silicon. Electron owns
the window and launches its bundled engine on 9765/9766 with the production
configuration. The dev app connects to the isolated source daemon on 7765;
see [local-development.md](local-development.md). A source service's legacy
default is not the desktop app's endpoint.

Claude's plugin finds the installed engine through `hooks/native.sh` and runs
`--integration mcp` or `--integration hook`. These modes only perform integration
work; they do not initialize audio or start a daemon. They default to 9765 and
respect an explicit endpoint override. Update app and plugin together.
The Codex preview currently uses uv for its separate adapter.

## The engine is its own app bundle

The frozen daemon ships as `Contents/Helpers/Noisy Studio Engine.app` (bundle id `pl.noisy.studio.engine`, `LSUIElement`, the app
icon), not as a bare executable - under `Helpers`, where macOS treats it as
nested code that `codesign --deep` validates, not as sealed data. macOS keys permissions to the code
identity of the process that asks: a bare PyInstaller binary had a random
ad-hoc identifier per build, so System Settings > Privacy & Security
showed a generic "exec" icon for it (#98) and every rebuild would have
lost the grant. Microphone and Input Monitoring are therefore listed
under **Noisy Studio Engine**; the Electron app itself asks for nothing.
Input Monitoring is requested only when the user picks a hotkey or
presses GRANT ACCESS in settings, never at boot (#97).

The bundle is a PyInstaller onedir tree (a bundle cannot be a single
file, and onefile unpacked unsigned libraries into a temp dir on every
launch - slow to start and impossible to notarize, #95).

## Signing and notarization (#95)

Downloads of an ad-hoc-signed app are refused by macOS as "damaged"; the
only fix users never see is a Developer ID signature plus notarization.
The release workflow does both automatically (since 3.0.0-alpha.7 the
repository carries the five secrets) and falls back to the unsigned build
when they are absent, e.g. on a fork:

| Secret | What it is | Where it comes from |
|---|---|---|
| `MAC_CERT_P12_BASE64` | Developer ID Application certificate + private key, `.p12`, base64 | Keychain Access on the Mac that requested the certificate: export the certificate WITH its private key, then `base64 -i cert.p12 \| pbcopy` |
| `MAC_CERT_PASSWORD` | the password chosen at export | same export dialog |
| `APPLE_API_KEY_P8` | App Store Connect API key, contents of the `.p8` file | App Store Connect > Users and Access > Integrations > Team Keys, role Developer or App Manager; the file downloads once |
| `APPLE_API_KEY_ID` | the key's ID | shown next to the key |
| `APPLE_API_ISSUER` | the team's issuer ID | top of the same page |

Requesting the certificate: developer.apple.com > Certificates, Identifiers
& Profiles > Certificates > "+" > **Developer ID Application** (not "Mac
Development", not "Apple Distribution"). It needs a Certificate Signing
Request from Keychain Access (Certificate Assistant > Request a
Certificate From a Certificate Authority, saved to disk). Only the Account
Holder can create Developer ID certificates, and Apple allows few of them,
so keep the `.p12` safe: losing the private key means the certificate is
unusable and must be revoked.

The build itself: `hardenedRuntime` with `build/entitlements.mac.plist`
(main app: JIT and audio input; helpers and the engine additionally
unsigned executable memory for cffi callbacks; library validation stays
on, since every library we load is signed with our Team ID), electron-builder
deep-signs the app including the engine bundle, and `notarize: true` makes
it upload to Apple's notary service and staple the ticket. The workflow then
prints `spctl -a -vv`, which must say `accepted` and `source=Notarized
Developer ID`. GitHub masks the secret values in logs; on a failed import electron-builder prints file paths and an unsalted sha256 of the export password, which is why that password is 32 random characters. An independent audit on 2026-09-15 confirmed no private material reaches the bundle, the release assets or git.

## Quality gates - nobody launches an alpha by hand to find out it crashes

Four checks, cheapest first, each catching a class of failure we have
actually shipped or nearly shipped:

1. **`npm run check:deps`** (runs automatically before `dist`, `dist:dev`
   and `dmg`): refuses to package when desktop's declared dependencies are
   not installed. A locally built app once crashed at launch with
   `Cannot find module 'posthog-node'` because `npm ci` had never run.
2. **The engine's `--version`** in the release workflow: the frozen daemon
   must report the tag's version, or the metadata is not bundled (#100).
3. **`uv run python scripts/smoke_integrations.py <engine>`**: initializes the
   frozen MCP server, discovers its speech tools, and executes the frozen hook
   entry point without starting audio. This checks the actual bundled modules.
4. **`scripts/smoke.sh <app> [version]`**: launches the built app with
   `NOISY_SMOKE=1`; the main process resolves its mode, waits for a daemon,
   prints one JSON line and exits 0 only if a daemon answered with the
   expected version. Production apps spawn their engine on a scratch port
   and config dir, so an installed copy is never touched. The release
   workflow runs it on every tag before uploading assets; locally
   `npm run smoke` (fresh dist), `npm run smoke:dev` (dev build, needs the
   dev daemon on 7765) or `npm run smoke:installed`.

The smoke test earned its keep on its first local run: the freshly built
app reported the PREVIOUS version, because the frozen daemon copies its
version from the venv's package metadata and `uv sync` had not run since
the bump. `build:daemon` now syncs first.

What this still does not cover: anything after the first window (rendering,
audio devices, permissions). Those need the daemon's own test suite and
Storybook, not a launch check.

