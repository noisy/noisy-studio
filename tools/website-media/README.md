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

The camera crop is a website prop (crew: 1.67× centered; hero: 1.75× with its top crop held at 20%), not baked into the
export. Hero thinking/console blocks come from this delivery's activity events,
not the previous take's manually edited timings. The original Studio journals contain scripted text. The website applies the
separately captured Grok transcripts described below.

`website/src/assets/todd/manifest.json` records source/output hashes, offsets and
encoding settings. The exporter checks that all three source files per scene
remain unchanged. Commit generated delivery files with the component changes;
retain the large originals separately. To revert, restore the website's previous
recording imports and remove the new take/poster/activity overrides.

### Actual spoken captions and incremental updates

The Todd website takes now use Grok transcriptions instead of the Studio script.
To regenerate captions, use the project's Python environment (with `websockets`,
`httpx` and `numpy`) and the already-configured xAI account. The command sends
only actor utterances from the original camera audio to xAI; it never sends the
mixed agent audio and never prints credentials:

```sh
PYTHONPATH=src python tools/website-media/transcribe_todd.py /path/to/fiver-todd-videos
python tools/website-media/transcript_timing.py
```

If the configured account belongs to the development instance, set
`NOISY_STUDIO_CONFIG_DIR` to that instance's config directory before running.
Do not copy keys into scripts or commit them.

`*-transcripts.json` preserves real streaming partial text and arrival timestamps,
plus a Grok batch transcription for the final, punctuated caption. Audio is fed
at recording speed. One second of decoder-only silence lets final words settle;
it does not extend the media. Capture includes one extra second of original actor audio after the Studio
end marker: Todd sometimes finished his sentence after pressing Space. Display
updates use their arrival times, bounded only by the video duration. Final
Grok punctuation is applied at the last captured update; a completed bubble can
therefore continue to settle after the actor turn ends. This
keeps all camera, agent reply and activity timings intact. Interim revisions longer than 1.5 times the completed line are suppressed to
avoid displaying duplicated Grok segments; raw captures remain intact.
The application step
reads the original journal and updates only transcript events and provenance.
The video exporter also reapplies these saved captions on future rebuilds.

The Todd crew export lacks the old camera-focus events. The authoring step
restores selector zoom 910 ms before Rex's first reply, and resets it 660 ms
before Luna's second reply, matching the original relative choreography. This
zooms the widget/agent selector only; the actor camera crop stays independent.
