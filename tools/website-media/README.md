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

## Original pre-Todd delivery sizes (historical)

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
It generates cropped H.264 CRF26 video, AAC128k audio, posters and derived journals.
Hero is 504×298; crew is 384×216. Consult the generated manifest for current byte sizes.

The approved crop is **baked into the exports**, controlled by
`tools/website-media/todd-framing.json`. Each rectangle is `[left, top, width,
height]` as fractions of the untouched source, followed by output pixel size.
FFmpeg rounds crops to chroma-compatible pixels. The former CSS zoom was
1.929375×, with a 20% top crop and 19.4286% left crop. Hero additionally accounts
for the approved taller frame's `object-fit: cover` horizontal crop; crew retains
the 16:9 framing. Hero's observed inner frame was 334.329×197.832 CSS pixels,
compared with the previous 854×480 full-frame export. The conversion uses
`r = (334.329/197.832)/(854/480)`, then
`left = (1-r)/2 + 0.194285714*r`, `width = r/1.929375`.
Both use `top = 0.2`, `height = 1/1.929375`; crew uses `r = 1`.

The website passes identity camera transforms in `website/src/toddCamera.ts`;
**do not reapply the old CSS zoom**. The approved inward hero layout is now the
default, including its raised console and centered opening widget. Old A/B/C
query parameters no longer change the layout. These exports are intentionally
small, sized for the embedded camera windows rather than full-screen playback.
If enlarging those windows significantly, regenerate from the originals at a
higher resolution instead of scaling up a previously encoded derivative.

Hero thinking/console blocks come from this delivery's activity events,
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

### Marked audio cleanup and reusable room tone

Both exports apply their `*-audio-edits.json` plans to the untouched actor audio.
The original sample intervals were rejected after headphone review, so **both
videos now use `tools/website-media/room-tone/todd-clean-room-tone.wav`**. Each
old sample interval is also repaired, alongside the user's marked repairs.
Adjacent intervals are merged before 12 ms crossfades, preventing the rejected
noise from leaking back at internal boundaries. No samples are removed or shifted.

The reusable WAV is 12 seconds, mono 48 kHz float PCM at −80 dBFS RMS (reduced 6 dB after headphone review). It is
**synthetic**, shaped from a smoothed median spectrum of quiet windows in both
originals; no recorded clicks, breaths or other waveforms are copied. Its FFT
construction is periodic, and the saved boundary is rotated to a tiny sample
step. It is longer than every current repair, avoiding short audible repetitions.
The sample's manifest records source hashes/windows, generator seed, output hash,
level variation and boundary measurements. These measurements do not replace
listening on headphones; audition the mixes before publishing.

Regenerate the reusable sample, then the site exports:

```sh
python tools/website-media/generate_room_tone.py /path/to/fiver-todd-videos
python tools/website-media/prepare_todd.py /path/to/fiver-todd-videos
```

Use the project's Python environment with NumPy and FFmpeg installed. The WAV
lives with authoring tools, not the website asset imports, so it does not add to
page downloads. Keep it and its generator for future footage; reevaluate its
level/spectral match if microphone or room changes. Original videos and marker
files on the Desktop remain untouched. Git retains the earlier delivery mixes
for comparison or rollback. To skip repairs for a scene, remove its plan from
the export directory and rerun; captions, crop and scenario timing are independent.

### Complete rebuild and future changes

Run from the repository root. Requirements: Python 3 with NumPy, plus FFmpeg and
ffprobe on PATH. The ordinary rebuild is local and needs no API credentials:

```sh
python tools/website-media/prepare_todd.py /path/to/fiver-todd-videos
npm --prefix website run build
```

Inputs to retain together:

- Both original `Todd - Hero Search.mp4` and `Todd - Crew.mp4` camera masters.
- The `hero-search*.json` and `crew*.json` Studio journals and their matching
  `.webm` reference recordings (exactly one journal per prefix in the input directory).
- Repository `website/src/assets/todd/*-audio-edits.json` repair plans and
  `*-transcripts.json` captured streaming captions.
- `tools/website-media/room-tone/` WAV, manifest and generator; the framing JSON.
- Agent MP3s in `tools/demo-recorder/clips/hero-lux-*.mp3` and
  `dashboard/src/components/marketing/crew-voice/`.

The recipe, in order:

1. Hash the original camera, journal and reference; read the recorded duration.
2. Repair the original microphone using the saved intervals and room-tone WAV.
   These markers use **original camera time**, before the synchronization trim.
3. Trim the camera and repaired microphone by the documented camera offset.
4. Crop the original 4K image, then downsize with Lanczos. Encode once to H.264.
5. Delay each original agent clip to its journal timestamp, mix with the repaired
   microphone, limit peaks, and encode AAC. No speech or silence is cut out.
6. Validate dimensions, duration and unchanged original hashes before replacing
   each website derivative. Extract its poster at two seconds.
7. Reapply saved partial transcriptions and crew focus events; derive activity
   markers from the original journal. Save provenance, hashes and framing in
   `website/src/assets/todd/manifest.json`.

For framing changes, edit only `todd-framing.json` and rebuild. For audio cleanup,
edit the repository repair plan using the original camera clock and rebuild.
Regenerate room tone only when its character/level needs changing. Captions need
no new API request for a routine rebuild: saved streaming captures are reused.
For a new actor/take, redo waveform alignment, repair markers and transcription;
old markers cannot safely be reused on a different recording.

The generator owns the derived journals/activity files: do not hand-edit those
outputs and expect edits to survive regeneration. Future timing refinements must
be made in the source journal or a separately persisted presentation plan.

**Original preservation:** the professional camera masters are outside Git in
the delivery directory, not archived by this repository. Keep a separate backup
of that whole directory before removing/moving it; the manifest's hashes verify
identity but are not a backup. Existing raw recordings of the previous actor are
unrelated and cannot reconstruct Todd's videos.

For rollback, restore the media, posters, manifest and website camera settings
from the same Git commit. Restoring only the old video while retaining identity
transforms would show the uncropped image. No deployment is performed by these
scripts.

Validated September 23 export sizes: hero 2,010,411 → 1,740,828 bytes (13.4%
smaller); crew 618,716 → 421,601 bytes (31.9% smaller). Both retain the previous
AAC packet hashes, exact video frame counts and stream durations. Combined MP4
size is 2.16 MB, down from 2.63 MB. Original camera hashes are unchanged.
