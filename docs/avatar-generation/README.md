# Voice avatar families

Eight generated families cover the complete 28-voice `SUBAGENT_VOICE_POOL` in `src/noisy_studio/listener/http_api.py`:

- `editorial`: illustrated people
- `matte`: softly sculpted people
- `painted`: painted people
- `mineral`: mineral forms
- `animals`: distinctive animal portraits
- `blobs`: expressive blobs with eyes
- `robots`: original robot personalities with science-fiction nods
- `agents`: Matrix-inspired black suits and sunglasses, using the human voice identities

The coverage audit includes [issue #44](https://github.com/noisy/noisy-studio/issues/44): Aurora and Liora were in the backend pool but absent from the frontend voice picker and old sprite mapping. Both are included in every new family. The pool and frontend catalog must match; `catalog.spec.ts` checks this independently of the hand-maintained artwork order. Other provider-specific or future unknown voices display a readable monogram and a development warning instead of disappearing.

## Assets and exact generation input

These images were generated with the built-in `image_gen` tool, not the fallback API/CLI. The exact prompt submitted for each production sheet is saved verbatim in `prompts/<set>.txt`. Generation does not guarantee pixel-identical results on a later run; use the accepted sheet as a visual reference when extending it.

The production PNGs live in `dashboard/src/assets/voice-avatars/`. Each sheet uses six columns and five rows. Cell indices are **zero-based**, row-major; the canonical ordering is `dashboard/src/avatars/voice-order.json`. Aurora and Liora occupy cells 26 and 27. Cells 28 and 29 are spare. Do not alphabetically reorder the artwork manifest: that would silently give existing voices different identities.

`VoiceAvatar.vue` clips the selected cell in CSS. Actual row and per-row column boundaries are recorded in `dashboard/src/avatars/crop-metadata.json` because generated grids are not pixel-perfect. Re-measure those boundaries when an atlas changes, then inspect every row for adjacent-art bleed. It retains the original generated image, including any alpha, without destructive cropping. The same component is used by the dashboard, voice picker, conversation bubbles and companion. The selected family is saved in `noisy-studio.avatar-set` in localStorage, shared across same-origin windows. It is a device/browser preference, not an account preference. Separate origins have separate preferences. The generated sheets are explicit Vite assets, so `/next/` deployments and the website resolve them correctly.

## Adding another voice

1. Confirm the new voice ID and metadata in the backend pool or provider. Update the frontend voice list too.
2. Append the voice ID to the manifest; never change an existing voice's index. Write a distinctive profile or silhouette specification. Preserve the same identity across the three human styles, and a distinctive mineral, animal and blob identity for the three non-human styles.
3. For each style, use its exact saved prompt and accepted sheet as the reference. Generate/edit **only the next spare cell**, preserving all existing cells and the six-by-five grid. Save that complete edit prompt under `prompts/updates/` with the voice ID and date; do not overwrite the original prompt history.
4. If the grid is full, create a versioned atlas and explicitly migrate the grid metadata; do not squeeze in a new row without updating the renderer and testing every existing assignment.
5. Inspect the avatar at 44, 72 and 96 px in Storybook's Product / Voice avatars / All sets, check gender/profile where applicable, cell boundaries, dark-background contrast and distinction from neighboring voices. Review Aurora/Liora and the last row as well as the first row.
6. Run the coverage, fallback and preference tests plus dashboard/Storybook/website builds. Test switching families, reloading, cross-window synchronization and a missing image. Commit the asset, exact prompt and mapping together.

## Review

Use Settings → Appearance to choose a family, or the Storybook All sets and Choose set stories to compare them. Names remain visible in the voice picker; artwork is an identity cue, not the only accessible label. Unknown voices and failed image loads retain their monogram fallback.

## Verification (2026-09-07)

- 214 frontend tests across 27 files pass, including backend voice coverage, missing-image fallback, preference persistence and complete-family preview switching.
- Dashboard typecheck/build, production Storybook build and website build pass.
- Rendered Settings / Appearance at 1280 × 800: all 28 selected avatars fit without right-panel scrolling (`clientHeight = scrollHeight = 480`); the family list scrolls independently.
- Selecting an animal family updates an already-open companion in a second same-origin browser tab without reloading; all three companion images report loaded artwork. Reload preserves the family.
- Opening the voice menu leaves Character at the same Y position and the rail height unchanged (`clientHeight = scrollHeight = 599`). Escape returns focus to the trigger. Avatar is 96 px and the text mute button is 76 × 48 px.
- Native Electron window behavior and OS-level PiP remain outside these browser checks. Importing user-created families is not implemented; the scrollable list accommodates additional catalog entries.
