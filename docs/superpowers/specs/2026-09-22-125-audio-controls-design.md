# Configurable audio controls — Storybook proposal for #125

Prototype only; no daemon, live dashboard, or persistence changes.

All nine controls live under Settings → Audio → Audio controls. Each control has a separately labelled checkbox controlling dashboard visibility. Hiding a control preserves its setting. Microphone device, Language, and Turn detection are visible by default. The microphone picker moves into this shared control set rather than remaining a separate settings-only control. The existing microphone level meter is outside this proposal.

The dashboard panel offers a Settings shortcut that opens the Audio tab at the Audio controls section and focuses its heading. With no controls selected, the panel retains that shortcut and a short explanation. Restoring default visibility affects visibility only, never audio values. In Push to talk mode, Auto-only timing controls remain in place but are disabled.

Storybook Lab/AudioControls compares A (compact visibility column) with B (explicit checkbox on each row). Both are interactive: settings and dashboard share values and visibility. The AllControls story checks the expanded layout. Prototype values and device names are synthetic.

Recommendation: B makes it clearer that a checkbox changes visibility, not whether an audio feature is enabled. A is denser for large screens. Choose the presentation before implementing production components. Persistence scope, real device refresh, provider capability states, and production navigation wiring remain implementation decisions after design selection. Do not silently change Batch/Live behavior as part of this visibility change.

Validation: build Storybook and visually inspect default, Settings, visibility changes, and all-hidden state.
