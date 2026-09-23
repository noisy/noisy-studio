# Website delivery assets

Keep originals. These are derived exports, not replacements for source recordings
or artwork. Run from the repository root with Python 3, FFmpeg/ffprobe and cwebp:

```sh
python3 tools/website-media/generate.py
```

The script reads the approved full-size mixed MP4 masters and original PNGs. It
never uses a previously optimized output as input. Raw microphone/camera originals
remain in `tools/demo-recorder/takes/hero-v1/original.webm` and
`tools/demo-recorder/takes/crew-v5/original.webm`. To reconstruct the approved mixes
from those raw originals, follow `tools/demo-recorder/takes/README.md` first, then
run this script. This additional delivery encoding is lossy video; audio is copied
without re-encoding, and there are no cuts or timing edits.

- Images: WebP quality 90, unchanged dimensions and sprite coordinates.
- Video: 854×480 H.264, CRF 24, slow preset, original cadence, MP4 faststart.
- Audio: packet-identical AAC stream copy from the approved mixed master.
- Output paths are fixed separately from input paths. Temporary files are checked
  before replacing delivery outputs. Never overwrite or delete an original.

`manifest.json` records original and raw archive SHA-256 hashes, generated asset
hashes, file sizes and tool versions. Generation checks input hashes before/after,
video duration, frame counts and audio packet hashes. Tool upgrades can change
encoded output bytes; inspect quality again after regenerating.

The website passes optimized MP4 URLs to the real shared scene components.
Storybook's ordinary recording stories keep the 720p master by default for crop
adjustment; full website stories use the website exports. The shared portrait
catalog uses the full-dimension WebP so the embedded dashboard benefits too.

## Revert

Restore the previous image references in `dashboard/src/avatars/catalog.ts` and
`dashboard/src/components/marketing/RecordedHeroScene.vue`. Remove the website
recording overrides from `website/src/scenes/HeroSceneG.vue` and
`website/src/CrewSection.vue`; the shared components then use their retained full
masters. No source restoration, audio reconstruction or re-recording is needed.

## Current delivery sizes

| Asset | Original master | Website derivative |
| --- | ---: | ---: |
| Portrait sheet | 1,732,042 bytes | 443,724 bytes |
| Wallpaper | 1,863,342 bytes | 260,182 bytes |
| Hero recording | 9,370,294 bytes | 3,944,386 bytes |
| Crew recording | 3,105,721 bytes | 1,306,355 bytes |

Combined: 16,071,399 → 5,954,647 bytes (62.9% smaller). This is full asset size,
not a claim about first-load traffic, LCP or measured page speed. Original masters
may still appear in the build because shared default props reference them; only
the website's selected delivery URLs are rendered. A later artifact-cleanup task
can separate their build graphs without removing the originals from the repo.

## Todd recordings (September 2026)

The website now selects `website/src/assets/todd/` exports. The old recordings
and their default Storybook scenes remain available. Keep the delivered camera
MP4s, browser-reference WebMs and matching JSON files together and untouched.
The original delivery currently lives outside Git at
`/Users/krzysztofszumny/Desktop/fiver-todd-videos`; do not delete that directory.
These small exports cannot replace the originals for future editing.

To reproduce from the original delivery (Python 3 and FFmpeg required):

```sh
python3 tools/website-media/prepare_todd.py /path/to/fiver-todd-videos
```

Camera timestamps lead the browser journal by 3.609375 seconds for Hero Search
and 3.109375 seconds for Crew. These offsets were measured by comparing the
reference and camera audio for every actor turn; no clock stretch was needed.
The exporter trims that lead-in, preserves the journal duration, and mixes the
existing agent MP3s at their recorded start timestamps with Todd's camera audio.
It generates 854×480 H.264 CRF24 video, AAC128k audio, posters and copied journals.
The resulting hero and crew videos are approximately 2.02 MB and 0.62 MB.

The camera crop is a website prop (currently 1.2×, centered), not baked into the
export. Hero thinking/console blocks come from this delivery's activity events,
not the previous take's manually edited timings. These Studio journals contain
scripted text, not live incremental transcription.

`website/src/assets/todd/manifest.json` records source/output hashes, offsets and
encoding settings. The exporter checks that all three source files per scene
remain unchanged. Commit generated delivery files with the component changes;
retain the large originals separately. To revert, restore the website's previous
recording imports and remove the new take/poster/activity overrides.
