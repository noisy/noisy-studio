# Website Product Showcase Implementation Plan

**Goal:** Replace the tactical marketing site with a graphite product showcase and current screenshots.

**Architecture:** Vue page sections compose current product components through the existing Vite alias. Static screenshot assets provide portable demonstrations; interactive character controls use local fixture state.

**Tech Stack:** Vue 3, TypeScript, CSS, Vite, Storybook.

## Global constraints

Keep Noisy Studio branding, synthetic screenshots and disabled live microphone demo. Base work on merged v3-desktop. Do not modify the daemon or original checkout. No automatic speech or deployment. Support reduced motion, keyboard access, root and subpath builds.

## 1. Visual foundation

- [x] Replace website/src/App.vue and website/src/style.css with a responsive showcase shell: navigation, large hero, product screenshots, companion stories, character section, setup and FAQ.
- [x] Use current waveform logo and product colors. Remove legacy avatar override and rotating slogans.
- [x] Build with `npm run build` in website; inspect browser at desktop width.
- [x] Commit the functional visual pass.

## 2. Current demonstration assets

- [x] Capture current dashboard and companion synthetic Storybook stories through the browser tooling. Save to website/src/assets/shots and inspect each image.
- [x] Correct scripts/marketing-shots.sh asset output synchronization and document source story/dimensions.
- [x] Verify the page uses new assets without broken images; build and commit.

## 3. Character and messaging

- [x] Simplify website/src/CharacterSection.vue into deliberate preset selection using current VoiceAvatar and CharacterReadout. Connect slider update events to local state. Avoid automatic preset changes.
- [x] Validate Claude Code and Codex-preview setup copy against README and docs/codex.md. Replace inaccurate offline, voice-count and installation-duration claims.
- [x] Verify presets, sliders, navigation and FAQ using browser controls. Commit.

## 4. Final verification

- [x] Build root and PAGES_BASE=/noisy-studio/ variants and inspect image requests.
- [x] Inspect page at 1440, 1280, 768 and 390 CSS pixels; resolve overflow and contrast issues.
- [x] Run relevant dashboard tests and inspect browser errors.
- [x] Record validation, push branch and prepare a PR against v3-desktop. Do not merge or deploy.

## Verification — 2026-09-08

Website root and /noisy-studio/ builds pass. The matching-base production preview renders and loads all 13 image elements; installation anchor works and no browser errors were recorded. Responsive layouts inspected at 390 and 768 CSS px, desktop initial render at 1280, and width checked at 1440; no horizontal document overflow. Character preset selection and keyboard Speed adjustment persist as a custom character. FAQ expands. Reduced-motion overrides reviewed in CSS; OS preference was not changed. All 219 dashboard tests pass; Storybook production build passes. Screenshot shell syntax check passes; captures for this change used browser tools rather than executing the headless capture script.
