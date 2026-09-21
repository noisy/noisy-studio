# Actor Demo Studio

The website build includes `/demo-studio/` (under `/noisy-studio/` on GitHub Pages). Start the website Vite server and open that path locally. It shares the production Companion and the existing Demo Studio scenario scripts and voice assets.

Rehearse requires no camera or microphone. Record captures the browser camera and microphone as a reference alongside an external camera recording. Use headphones. The external camera is started separately; match its audio to the reference recording during editing. Clap once or use a clapperboard in view of both cameras after starting both recordings. An optional sync-marker records a named timestamp alongside that cue.

Space completes the current user line, shows activity, then plays replies in order. Text comes from the supplied script, not speech recognition. Exported transcript events explicitly record this source. No credentials, provider requests, backend, or automatic upload are involved.

Download both the original recording and timing JSON. The version-1 JSON preserves existing user-start/end, transcript and agent-start/end conventions, adding activity-start/end and sync-marker events. Timing is relative to the MediaRecorder start event. Agent start is logged when playback actually starts, not when it is requested. Existing editing tools can consume the take conventions; external-camera media must first be aligned to the microphone reference. Retain both originals.

Run `npm test --prefix website` for timing, interruption and media boundary tests. A physical camera/microphone test needs permission in the browser and is not simulated by these tests.

The hero-search scenario derives every pause from the homepage's original take and saved presentation edits through `recordedActivitySchedule`. This includes quiet intervals and activities before replies and after replies, before the actor's next line. Actor delivery remains free-paced; Space anchors the following authored gap. Labels come from the shared `CONSOLE_ACTIVITIES` mapping. Other scenarios retain their authored reply pauses.

After recording, Studio renders a stereo 48 kHz PCM WAV of agent speech entirely in the browser. Each clip starts at its captured agent-start timestamp and is clipped at agent-end or the take end. The original actor recording is never re-encoded. Download ZIP packages both, the timing JSON, used MP3 source clips and editing instructions. Archives are prepared before the download link appears. Separate original/timing downloads remain available if audio preparation fails.

The finished-take player uses the original media as the clock for the widget and aligned agent track. Pause, seek, playback speed and volume apply to the conversation preview. Open an existing take by selecting its original media and matching version-1 JSON together. For externally filmed video, the preview shows the browser reference until the external original is aligned separately.
