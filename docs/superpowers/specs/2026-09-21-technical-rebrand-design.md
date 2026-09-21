# Independent technical rebrand on main

Status: approved by Krzysztof on 2026-09-21; implementation in progress.

## Goal and evidence

Make Noisy Studio the canonical product and technical identity, independently of PR #90. Work on main in small local commits; do not push, publish, or modify host integration configuration. PR #90 is open, conflicting against v3-desktop, and includes obsolete Docker work. Do not apply its patch.

Current main already uses noisy-studio in the Claude/Codex plugin manifests and Claude marketplace. Remaining identities include the Python distribution/import package, CLI entry points, engine executable, environment prefix, an agent marketplace manifest, browser preference keys, config paths, and desktop identity. The bundled engine already has the Noisy Studio name and pl.noisy.studio.engine identifier. The desktop shell still has a legacy bundle identifier. Current desktop code and documentation also disagree on the default config location: noisy-coding-app versus noisy-coding. Resolve this from actual launch paths and tests rather than assuming the documentation is authoritative.

## Options

1. Recommended: canonical rename with bounded compatibility. New code, installs, writes, examples, and build artifacts use noisy-studio. Old spellings survive only where required to recognize existing installations, migrate data, or keep existing integrations connected. Inventory and test each exception.
2. Hard cutover with no old strings: removes compatibility but breaks old entry points, environment overrides, settings discovery, and hook registrations. Conflicts with the requirement to avoid breakage.
3. Cosmetic rename only: lowest migration risk but leaves the requested technical rebrand unfinished.

## Proposed boundaries

- Rename the distribution and source package to noisy-studio/noisy_studio together with all imports, dynamic imports, metadata lookups, build paths, tests, and CLI consumers. New CLI names are canonical; retain old entry points as explicit upgrade aliases. Check whether installed source MCP processes need an import compatibility shim before moving the package.
- Introduce one environment-resolution policy: an explicitly supplied NOISY_STUDIO_* value wins, including an empty value where meaningful; the matching old prefix is fallback only. Apply this to Python, standalone hooks, shell launchers, Vite, desktop startup, and spawned subprocesses. Never silently fall back to production when dev configuration is supplied.
- Use new names for fresh config stores and preference keys. Existing stores must be detected without overwriting or silently combining independent histories. Explicit directory overrides remain authoritative. Inspect database/WAL handling and concurrent old-process access before choosing a migration mechanism. Keep the live dev store in place until its postponed restart; never move data under a running process. Preserve credentials, provider settings, conversations, voice ownership, registration recovery, and microphone settings.
- Update canonical integration names and hook matching together. Recognize old MCP tool prefixes while sessions transition. Installer migration must update only owned registrations and prevent duplicate hooks. Do not edit the user's host configuration as part of repository implementation.
- Rename the bundled executable and every consumer together, including signing/build scripts, shell discovery, release smoke checks, and desktop tests. Keep old installed-bundle discovery as a documented upgrade fallback where necessary.
- Migrate renderer preference keys without losing accent/avatar/cue settings. New values take precedence when both names exist; migrate once rather than repeatedly restoring old values.
- Preserve the existing macOS application identity until a separately verified signed upgrade can establish that renaming it preserves permissions and application identity. Document this as an OS compatibility exception, not an incomplete text replacement. The already renamed engine identity stays unchanged.
- Update current documentation, repository links, package/lockfile names, skills, and examples. Inventory historical documents and media separately; do not falsify old commit IDs, issue text, or recorded history. Do not rename the user's checkout or touch the unrelated untracked maintenance script.

## Verification and rollout

Start with a tracked-file inventory and baseline checks. Implement independently in coherent stages: compatibility foundations, Python/build rename, integration and launcher changes, preference migration, documentation and residue audit. Each stage must be functional and checked before a local commit.

Test old-only/new-only/conflicting environment settings, fresh and existing stores, dev/production separation, migration conflicts and repeated startup, old/new MCP identity recognition, installer idempotence, and preferences. Verify actual package installation and CLI entry points; run Python unit/harness suites, frontend and desktop checks/builds, then build a frozen engine and exercise real MCP/hook protocols. Audit remaining old-name matches against the explicit compatibility inventory.

Do not claim macOS signing/permission preservation from unit tests. Report any signed-install upgrade validation still required before release. Only after the code and packaging checks pass, use the 60-second postponable dev restart, verify the exact config store, Jabra microphone, existing conversations, dashboard connection, and spoken round trip. No push or public PR/issue update without authorization.
