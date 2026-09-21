# Interface redesign verification — 5 September 2026

Worktree: `/Users/krzysztofszumny/Developer/noisy-studio-redesign`

Branch: `feat/interface-redesign`, based on `890dfc6`.

## Implementation

The dashboard now uses graphite surfaces, system typography, restrained state colors, a compact header, a conversation-first layout, and native sliders for character settings. Settings adapt to the available panel width. The companion has an explicit session/status header, readable conversation bubbles, and a persistent row of session buttons. The desktop session header also serves as a labeled drag handle, saving space for history.

Review refinements replace the tactical turn ring with a horizontal speech timeline and speaker counts, match the header actions at 40px, and promote the development-only badge to a prominent amber label. A shared typographic voice avatar replaces pixel portraits: 48px in dashboard messages, 72px in the voice panel, and 44px inside 48px companion session buttons. All runtime consumers and the voice gallery use that component.

Transparent mode leaves the companion's outer surface clear. Message and control backgrounds remain readable over light and dark workspaces, with contrasting outlines; the labeled drag header has alternating light/dark edges. Resize observation now includes the window container so height-only resizing refits the history. The native Electron window already enables transparency and loads `?transparent=1`; no desktop process change was needed.

Existing API contracts and voice/session actions remain in place. Additional accessibility work includes native voice-picker buttons, focus restoration, labeled inputs, keyboard-accessible conversation scrolling, mute pressed states, and an inert dashboard behind onboarding. Hidden companion content is inert until floated.

Storybook includes the real dashboard and companion window backed by an isolated daemon fixture. Provider/download stories use the same fixture infrastructure. Storybook has no daemon proxy, and the microphone input is mocked. No runtime dependencies were added.

## Commands and results

| Directory | Command | Result |
| --- | --- | --- |
| `dashboard` | `npm test` | 202 tests passed in 23 files; baseline was 180 tests in 20 files |
| `dashboard` | `npm run build` | TypeScript and Vite production build passed |
| `dashboard` | `npm run build-storybook` | Production build passed, 256 modules |
| `website` | `npm run build` | Vite production build passed, 74 modules |
| repository root | `node --check desktop/main.js` | Passed |
| repository root | `git diff --check` | Passed |

Final command logs are available locally at `/private/tmp/noisy-redesign-{tests,dashboard-build,storybook-build,website-build}.log`.

The frontend tests still emit the baseline happy-dom connection warnings for localhost:3000; all tests pass. Storybook reports dependency eval and large documentation-chunk warnings. A development indexing error after hot configuration reload cleared when the task's own Storybook process was restarted; the independent production build passed.

## Rendered inspection

Screenshots were inspected in the connected browser before implementation and throughout the redesign. The final inspection covered:

- Dashboard at 1440 × 900, 1024 × 600, and 390 × 844.
- Conversation, recording, speaking, unheard/queued, muted, offline, service error, empty, setup, settings, and scheduled restart states.
- Long session names and long unbroken URLs. At 390px, document width remained 390px and conversation content stayed within its 321px panel.
- Settings with long device names: 321px available width and 321px content width after the responsive fix.
- Companion at 460 × 400 and 320 × 240, including speaking, recording, working, unheard, muted, disconnected, and long-name states.
- Actual companion window wrapper at 320 × 240, including its drag-strip space and bottom session controls.
- Shared dashboard and character compositions used by website consumers, plus a provider-download Storybook state.

The follow-up inspection covered the redesigned history and avatars at 1440 × 1200, and the header at 390 × 844. Both header actions measured 40px high in normal and muted states; the amber development badge remained visible at 34px high, with no horizontal page overflow.

Synthetic companion screenshots now default to an explicit 540px widget width, replacing the content-driven 863.5px width measured in the Claude Code voice-fix scene (37.5% narrower). The same width applies to wallpaper presets, and both story groups expose a width slider. Rendered checks of the terminal scene and long-refactor wallpaper confirmed a 499px thread with no horizontal overflow. The Storybook production build passed after this refinement.

New Product/Companion transparency stories show the actual window composition over white, dark, and colorful workspaces, plus a 280 × 200 minimum-size preview. Screenshots confirmed visible backgrounds between messages and controls. The companion surface computes to `rgba(0, 0, 0, 0)` and the labeled header to `-webkit-app-region: drag`. A 420 × 280 window provided 142px of visible history for 372px of messages; Home and End reached scrollTop 0 and 230. The 280 × 200 preview kept its card within the window (8px inset, 184px card height), with 62px of visible history and persistent session controls. Height-only resizing of the actual window story from 200 to 280px grew the history from 62 to 142px. Its Storybook host explicitly supplies viewport height to match the real app root.

Keyboard checks reached both ends of a 1494px conversation inside a 465px feed (scrollTop 0 and 1029). Selecting Code review updated both the viewed heading and receiving label. Keyboard dismissal of an offline session worked. Escape closed the voice picker and restored its visible 2px focus outline.

Isolated interaction checks also covered microphone mute, per-session mute, voice selection, character slider adjustment, playback pause, skipping all unheard replies, and restart postpone/cancel. Existing component tests cover replay, transcript cancellation, session ordering/dismissal, state transitions, and emitted character patches. Added tests cover companion state/routing/waiting labels, compact unheard status, portrait mute actions, and picker focus restoration.

Measured token contrast against the main panel: primary text 13.72:1, secondary text 6.68:1, and the blue/amber/violet/green/red text accents all above 7.8:1. CSS suppresses transitions and animations under reduced motion; the companion's animation loop also respects that preference on mount. Only the graphite theme is shipped.

## Review views and limits

### Reported Storybook error audit

The reported dashboard error did not reproduce after fresh navigation. The browser retained an earlier Vite reload failure for the removed `SessionRing.vue`; that is evidence of stale development state, but the exact user-reported error was not captured. All 114 indexed stories were opened in the connected browser and checked after reaching their rendered state: no error screens or new console errors were observed. This was a catalog-wide render smoke check, not a complete visual or interaction audit of every story.

Two separate Storybook problems were corrected:

- The status-board story replaced all `window.fetch` requests and never restored the original function. Its fixture now intercepts only the two same-origin speech-test endpoints with matching HTTP methods and restores fetch when the story is disposed. Six regression tests cover fixture responses, unrelated/index/foreign-origin requests, and cleanup. The failing-pipeline story's Run All action produced two pass and two failure cells; sidebar navigation back to Dashboard/Conversation rendered successfully.
- The dev server watched `storybook-static/iframe.html`, causing open previews to reload during validation builds. The generated output is now excluded from its watcher. After restarting only this worktree's port-6007 server, a full Storybook build produced no preview-reload events or dev-server errors, and all four visible status-board results survived the build. The server log is `/private/tmp/noisy-redesign-storybook-dev.log`.

The dashboard and Storybook builds passed after these fixes, alongside the 202-test suite. The dashboard review link was left open after successful sidebar navigation.

- [Dashboard](http://localhost:6007/?path=/story/product-dashboard--conversation)
- [Companion](http://localhost:6007/?path=/story/companion-widget--claude-speaking)
- [Companion window](http://localhost:6007/?path=/story/product-companion-window--conversation)
- [Transparent companion over white](http://localhost:6007/?path=/story/product-companion-transparency--light)
- [Transparent companion over dark](http://localhost:6007/?path=/story/product-companion-transparency--dark)
- [Smallest companion window](http://localhost:6007/?path=/story/product-companion-transparency--smallest-window)
- [Long dashboard content](http://localhost:6007/?path=/story/product-dashboard--long-content)
- [Compact unheard replies](http://localhost:6007/?path=/story/companion-widget--pending-replies)

Product controls were exercised against fixtures. The user's daemon, live credentials/devices, original checkout, and other worktrees were not modified. Native Electron dragging, always-on-top behavior, and a real browser PiP window were not exercised; the shared window component and desktop entry-point syntax were checked. Reduced-motion rules were reviewed in source and the companion tests use the reduced-motion branch; the host OS preference was not changed. This is not a complete screen-reader audit. No merge, deployment, or release was performed.

## Laptop density follow-up — 2026-09-07

Reduced dashboard chrome, microphone plot height, sidebar panel padding, audio-control row spacing, and character/history spacing. Trait descriptions now share the heading row with their values. Push-to-talk and microphone mute share a row; the duplicate lower Settings button was removed while the header action remains. Voice avatars remain 72 px. Overflow remains available for smaller windows or unusually long content.

Browser measurements and rendered screenshots confirmed both sidebars fit without vertical overflow at 1280 × 800 (including push-to-talk) and 1496 × 838 (automatic detection). At 1280 × 800 the left sidebar measured clientHeight/scrollHeight 675/675 and the right 520/520. The offline scenario also fitted. At 390 × 844 the document had no horizontal overflow. Keyboard ArrowRight changed Humor from 40 to 60 and updated its description to playful.

Added Product/Dashboard/Laptop with a 1280 × 800 viewport preset and verified that the Storybook toolbar applies those dimensions. The original 114-story smoke check above predates this additional story; this follow-up used focused render checks. All 202 tests in 23 files passed; dashboard typecheck/build, Storybook build, and website build passed. The native desktop application was not restarted or modified during validation.

## Conversation chrome and companion review — 2026-09-07

Removed the repeated conversation heading and generic subtitle. The selected tab now shares the panel surface and joins its upper border; a Mic marker identifies the transcript recipient even when another tab is viewed. Telemetry uses compact inline groups (about 48 px at 1280 × 800), and the push-to-talk hints no longer wrap unnecessarily. At that viewport both dashboard rails remained free of overflow. ActivityLine now says “Agent activity” instead of assuming every agent is Claude; its existing tests cover tool activity, speech and idle states.

Addressed PR comment 5564545867: the native companion's host fills the user-sized window, with fixed grid rows for the drag header and controls and a flexible, bottom-anchored scrolling thread. Transparent mode reveals its outer frame and header on hover (also keyboard focus), with a top fade and quiet scrollbars. Browser hover is scoped to the companion instead of the whole preview page. Standalone embedded cards retain their existing bounded-growth behaviour.

Rendered checks covered 420 × 280, 280 × 200 and a new UserSizedWindow story at 420 × 500. Switching from a populated conversation to an empty one preserved header/control coordinates and component height. In the 500 px window the thread retained its 367 px viewport after switching, rather than collapsing to the default 220 px request. At rest the header opacity was 0; interacting revealed both header and frame with opacity 1. Native Electron dragging/resizing and real PiP remain unexercised; these checks concern rendered geometry, not OS window operations. All 202 tests passed, and dashboard, Storybook and website builds passed.
