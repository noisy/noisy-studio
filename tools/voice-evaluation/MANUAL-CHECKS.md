# Live speech checks

The user chose to perform the physical microphone check on 2026-09-18. Storybook uses fixtures: perform these checks in the running app built from this branch, not in Storybook. Automated tests and the isolated real-model HTTP run are separate evidence, not proof of microphone permissions or audible output.

## Local microphone test

1. In Settings → Speech → Your speech, choose a prepared local recognizer. Leave your current working selection active while testing the candidate.
2. Pause the main microphone if the app asks. Start the microphone test explicitly, allow microphone access, speak a sentence, then finish. Check that the final transcript appears and no message reaches a coding agent.
3. Start another test and Cancel while speaking. No late result should replace the previous result. Close settings during a test and confirm that recording stops.
4. Try a short sentence with a filename or number, and a Polish sentence if relevant. Note the selected language and exact words that were wrong; the existing English demo recordings do not establish Polish accuracy.
5. Apply only if satisfied, then explicitly resume the main microphone. Check a normal conversation and switch back to the previous engine to confirm it still works.

## Agent voice playback and switching

1. In Agent voices, select a prepared local candidate. Listen to two distinct mapped voices; stop a sample and close settings while another is playing. Playback should stop promptly.
2. Apply the reviewed mappings. Confirm an actual agent reply uses the selected voice.
3. Switch back to the previous engine. Its reviewed assignments should return. Recognition selection should not change.

## Cloud check, when authorized and configured

Cloud previews send the supplied audio/text to the selected provider and may incur normal API charges. No cloud comparison was run during this verification pass.

Check one normal streaming conversation, cancellation during playback, and a recoverable network failure. Verify the UI reports the actual mode (browser output may be batch), failure is actionable, and a local selection never silently switches to a cloud engine.

Record the app commit, engine/model, input/output device, language, result and any reproduction steps. Avoid including credentials or unrelated conversation content.
