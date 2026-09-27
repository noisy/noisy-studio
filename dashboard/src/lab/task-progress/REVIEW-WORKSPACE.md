# Review workspace exploration (#172)

These stories render the actual dashboard against Storybook's fictional daemon fixture. The task panel is inserted only by the Lab wrapper; production App remains unchanged. Six 25px rows pair a named conversation with a thin task-count bar. Completed work with an explicit target gets Review instead of a percentage. Opening a result is not approval.

Review placement alternatives:

- **Floating controls:** movable in-app panel preserves the artifact canvas. Drag its handle or use keyboard-accessible Left/Right controls.
- **Top strip:** controls stay above the artifact; useful when its width matters more than height.
- **Side dock:** stable controls beside the artifact; sacrifices canvas width.

All placements identify the responsible agent as the feedback recipient. Push-to-talk is press/release (also Space); Auto explicitly names the listener and offers a synthetic feedback button. No audio is captured, no message is sent, and no live recipient changes. Sample transcript bubbles are labeled as unsent previews.

Approve result opens a separate confirmation. The simulated approval has Undo. Opening, visiting, holding to speak, or sending feedback cannot approve a result.

The artifact is static local `srcdoc` in a sandboxed iframe without scripts or permissions. Cannot Embed models the fallback to an external tab, retaining review controls. There is no cross-origin inspection, embedding-policy bypass, microphone permission request, or native/OS widget.

Live integration and URL trust policy require a separate implementation decision after design review.
