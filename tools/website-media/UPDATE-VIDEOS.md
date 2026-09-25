# Updating Noisy Studio demo videos

This is the handoff for a future request such as **“update all demo videos after
changing the widget, wallpaper, or Todd recording.”** Decisions approved on
September 24, 2026. Keep them unless explicitly asked to change them.

## Deliverables and approved presentation

| Destination | What to generate | Opening |
| --- | --- | --- |
| Website hero | Small cropped Todd video, poster, journal and activities | Keep the website's original console/widget entrance choreography. |
| Website crew | Small cropped Todd video, poster, journal and activities | Keep the agent-selector focus animation and original dialogue order. |
| Shareable hero movie | Complete rendered scene, with mixed sound | Short Noisy Studio logo/logotype + “Coming soon”, then full hero animation. |
| GitHub README | Complete rendered scene, with mixed sound; filename **Demo.mp4** | **No logo, no intro, no entrance animation. Console and companion widget are already settled in their final positions; widget is bottom-right.** |

The README first frame must show the actual product scene, not a logo/title card.
Use the `?readme` export mode, **not a time cut of the ordinary movie**: Todd starts
speaking before the website entrance animation ends, and cutting that animation
would remove part of his sentence. Preserve the entire dialogue and its timing.

Capture the real Vue components: wallpaper, Claude console, companion, Todd's
camera and all timed captions/activity. Do not recreate the widget as artwork.
Keep the approved crop and inward hero-camera layout. Export landscape
1600×900, 30fps H.264/AAC MP4; fit the whole 1200×760 scene without cropping it.
The interactive mute button is omitted from exported movies.

GitHub converts spaces in uploaded filenames to dots and adds a filename header,
even for a direct HTML video embed. Custom title/aria-label did not replace it in
our preview tests. **Upload as `Demo.mp4`**, with no technical suffixes. Put the
bare attachment URL after the opening README description and before “Install”.
This keeps the binary outside Git history. Verify the first frame and player in
the rendered README after replacement; do not assume GitHub's preview behavior.

## Choose the rebuild scope

- **Wallpaper, widget, console, colours, or layout changed:** rerender both full
  hero movies. The small Todd camera files need no re-encoding unless their frame
  or required resolution changed. The website uses real components directly.
- **Actor recording, crop, audio repairs, or dialogue/timing changed:** regenerate
  the affected website media/timelines first, then rerender both hero movies if
  hero changed. Crew-only changes do not require rerendering the hero movies.
- There is currently no standalone full crew-scene movie exporter. “All videos”
  means the four deliverables above, not an invented additional crew movie.

## Inputs and originals

Original delivery location at authoring time:
`/Users/krzysztofszumny/Desktop/fiver-todd-videos/`.

Keep both original 4K camera MP4s, matching browser reference WebMs, Studio timing
JSONs and supplied repair JSONs. They are **outside Git**; optimized exports cannot
reconstruct them. Back up the entire delivery directory separately before moving
or deleting it. If moved, pass its new path to the scripts. Hashes and offsets
are recorded in `website/src/assets/todd/manifest.json`.

Repository inputs:

- `tools/website-media/todd-framing.json`: approved crop rectangles/output sizes.
- `website/src/assets/todd/*-audio-edits.json`: original-camera-time repair plans.
- `website/src/assets/todd/*-transcripts.json`: captured real streaming captions.
- `tools/website-media/room-tone/`: approved quiet replacement background.
- Agent MP3s, source journals, and waveform alignment: see [README.md](README.md).

Do not apply old timing/repair markers to a new actor take. Redo waveform alignment,
transcription and markers first. Do not adjust activity timing merely because the
visual design changed. Never overwrite source recordings with delivery exports.

## Rebuild commands

Run from the repository root. Requirements: Node.js, npm, Chrome, FFmpeg/ffprobe;
Python with NumPy for camera/audio regeneration. Use the project Python environment.

If the camera/audio inputs or framing changed:

```sh
python tools/website-media/prepare_todd.py /path/to/fiver-todd-videos
```

This rebuilds website hero and crew exports from originals, applies audio cleanup,
mixes original agent clips, reapplies saved partial captions and writes posters
and provenance. It does not call transcription APIs during a normal rebuild.
For new transcription or room-tone generation, follow [README.md](README.md).

Install dependencies if necessary, then start the local export page:

```sh
npm ci --prefix dashboard
npm ci --prefix website
npm install --prefix /tmp/noisy-video-renderer playwright --no-audit --no-fund
npm --prefix website run dev -- --host 127.0.0.1 --port 5214
```

In another terminal, create both movies outside the repository:

```sh
node tools/website-media/render_hero.mjs /path/to/exports/noisy-studio-hero.mp4
node tools/website-media/render_hero.mjs /path/to/exports/Demo.mp4 'http://127.0.0.1:5214/hero-export.html?readme'
```

Use a new output directory for a new revision: the renderer overwrites its output.
For a different port, pass the explicit export-page URL to both commands.
`RENDER_NODE_MODULES` can point to another isolated Playwright installation.
Current capture timeout is 100 seconds; extend it in `render_hero.mjs` before
rendering substantially longer future scenarios. Allow real playback time plus
encoding for each movie. Keep the export tab/scene code unchanged during capture.

`website/hero-export.html` is a dev-only authoring page, not a production build
entry point. It imports `website/src/hero-export/HeroExport.vue`, which reuses
`website/src/scenes/HeroSceneG.vue`. The `readme` mode fixes the initial positions.
`render_hero.mjs` captures frame timestamps, aligns the original mixed audio, and
removes capture warm-up in README mode. Its `.mp4.json` sidecar records the offset
and temporary frame directory; neither the movie nor frames belong in Git.

## Verify and deliver

1. Inspect the first frame: README has the console and bottom-right widget already
   in position; shareable version starts with the branded opening.
2. Watch the start, a speaking segment in the middle, and the final reply. Check
   lip sync, incremental captions, thinking/console activity and the final words.
3. Check dimensions, audio presence, duration and file size with `ffprobe`. Decode
   the whole output with `ffmpeg -v error -i /path/to/exports/Demo.mp4 -f null -`.
4. Check the website hero and crew if their assets changed. Run
   `npm --prefix website run build` after component changes.
5. Preserve originals and prior exports; commit changed scripts/docs and selected
   website derivatives together. Do not commit professional masters or full-scene
   movies. Export code was initially on `codex/hero-video-export`; ensure the
   working checkout includes it rather than assuming it is on production main.
6. When publication is authorized, upload **Demo.mp4** via GitHub's Markdown editor,
   copy the new attachment URL, replace only the old README demo URL, and publish
   that README change. Uploading does not update the previous attachment in place.
7. Verify the actual repository README shows `Demo.mp4`, loads the new scene and
   plays sound. Publish website asset changes through its ordinary deployment
   workflow separately when requested.

Current approved README attachment can always be found in the root `README.md`;
prefer that over a stale copied URL in this guide.
