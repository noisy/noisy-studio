---
name: dashboard-design-language
description: The Noisy Studio dashboard's design decisions — color semantics, the fixed-slot rule, blink rules, overlay-not-push, conversation-scoped layout, geometry as script constants, and the Storybook-first workflow. Repo-local skill; consult BEFORE styling or adding any dashboard UI so new work speaks the established language.
---

# Dashboard design language

Decisions made deliberately (2026-07-21 session, with Krzysztof calling
each one) — not derivable from the code alone. New UI must speak this
language; deviations are a conversation, not a default.

## Color semantics — one meaning per color, everywhere

- **red** — muting and errors, nothing else. All mute signals are red and
  share the alarm look (MUTE MIC, muted portrait wash, muted tab glyphs).
  Never use red for a status like "waiting".
- **amber** — messages waiting / degraded-but-working.
- **green** — speaking right now, and good news (update available).
- **violet** — agent working/thinking. Always via `var(--violet)` /
  `color-mix(in srgb, var(--violet) N%, transparent)` — never hardcoded
  rgba; retinting must stay a one-variable edit in `hud.css`.
- **cyan** — structure, chrome, resting text. The neutral of this UI.

## The fixed-slot rule

A state change NEVER changes an element's size. Status glyphs render
inside a fixed-size slot (tab statusslot); label swaps get a `min-width`
sized for the longest label (MUTE/MUTED button); hover affordances (tab
✕) are overlays that reserve or overlay space. If toggling something
makes neighbors shift, it's a bug.

## Blink rules

- Only the LABEL/color pulses — the plate/background stays rock solid.
- The dim phase stays readable: a pulse, not a blackout (≥ ~0.5 opacity
  or a dimmer color, tuned by eye).
- All mute-related blinking shares the cadence: `1.6s step-end infinite`.

## Overlay, don't push

Anything that expands (voice-picker list, dropdowns, badges) overlays on
the z-axis over what's below — column heights never jump. Solid opaque
backdrop (`--panel-solid`) + shadow so it reads as a layer.

## Layout architecture

Conversation-scoped things (log, telemetry strip, catch-up button,
persona rail: portrait + character + session ring) live INSIDE the
conversation frame. Machine-global things live in the header: two
labelled groups, YOU · INPUT (mic meter + one mic slot) and AGENTS ·
OUTPUT (mute all), then Settings (option C, 2026-11-27). The mic slot's job
follows the turn mode - Mute mic in Auto, Hold to talk in push to talk
(muting means nothing there) - and a mute left over from Auto shows as
"Mic muted" in the same slot, never as a dead button. The telemetry/catch-up
width = the bubbles column only, never under the rail.

The conversations are a vertical list in the left column, grouped by
PROJECT (v3, 2026-11-27): a project is the session's repository (worktrees
fold into it), its heading is badge + name + an amber count of messages
waiting for you there; conversations without one gather under "No project"
at the end. Projects keep a stable order and never re-sort on state - there
is no "Working" section: projects are always busy, so working is a row
glyph. "Settled" (ended; folded by default) sits below. A folded section
never hides the viewed or mic row, nor one with messages for you. The mic
row carries an inset green edge (no "Mic" word: the edge says it). The Tab
hotkey is drawn as a key with the real chord ("F17"), never a bare number that
reads as a count; on rows it shows on hover/focus only (the user knows their
keys), and right-click assigns one (a position swap: the daemon numbers by
position). An idle row has an EMPTY status slot - a grey dot read as a bullet. The selected row
is highlighted, NOT fused with the frame - fusing breaks as soon as the
list scrolls. Grouping and order live in `agentOrder.ts` (the widget uses
the same order); drag-and-drop reorders within a project only.

## Geometry as script constants

Tunable dimensions are named constants at the top of the component's
script (`THUMB_PX`, `VISIBLE_ROWS`), flowing into CSS via CSS vars — "I
hoped this was one variable" should always be true. Remember
`box-sizing: border-box` whenever a border must live inside the stated
size (the 77px-avatar lesson).

## Process

- New component ⇒ its own file + Storybook story + spec, in the same
  change. Components stay small; App.vue must not grow.
- Explore concepts as throwaway Storybook boards (mock HTML variants
  A/B/C) **under `Lab/`**, let Krzysztof pick, THEN implement in the real
  component and collapse the boards into one canonical state-matrix story.
  A `Lab/` story is promoted or deleted; it does not live there forever.
  This rule existed and was not followed - 43 stories accumulated four
  naming styles, proposals sitting beside finished components, and two
  entries loose at the root (#116).
- Tune scoped-CSS replicas in Storybook, then port back (tabsbar).
- **Storybook has four sections and only four**: `Dashboard/` (main window),
  `Widget/` (companion), `Website/` (marketing components and the
  synthetic-screenshot rigs), `Lab/` (proposals). Nothing at the root.
  Title is `Section/Component`, where Component is the **file name** in
  PascalCase - so the sidebar and the filesystem answer the same question.
  States are stories inside the file, never separate titles, and titles
  carry no annotations like "(proposal)" or "Concepts": that is what the
  section is for. Full conventions in `dashboard/.storybook/README.md`.
- Storybook is published from `main` at <https://noisystudio.ai/storybook/>,
  so a story can be cited by URL. Its title shows the commit it was built
  from. A broken story fails the deploy - it is a reference, and a
  reference that lies is worse than none.
- Verify visually with headless-Chrome screenshots
  (`--headless --screenshot` + sips crop) — don't ask the user to be
  your eyes for pixel checks.
