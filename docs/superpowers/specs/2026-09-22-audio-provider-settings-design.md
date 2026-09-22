# Audio shortcut and provider-aware Settings proposals

Storybook Lab/AudioControlOptions compares More, More…, More ↗, More →, and More with a sliders icon. Each uses the actual AudioControls panel with a presentation slot; its production default remains More… until selection.

The ProviderAvailability story demonstrates Grok, Whisper/Kokoro, and English-only Whisper/macOS setups without changing real providers. Recognition and speech modes are independent. Unsupported mode choices stay visible with a readable reason and a change-engine link. Mode-dependent restrictions explain their remedy rather than suggesting an unnecessary provider change. Noisy Studio's local Auto/PTT controls remain available with every engine.

Language copy names both directions, explains that provider/model language support differs, and avoids declaring unknown or undocumented support impossible. The language row is intentionally illustrative, not a working picker: deciding how to present two different language contracts behind today's one shared value remains part of the design review. Do not silently intersect language codes, discard saved values, or disable visibility customization just because the current engine lacks a feature.

After selection: wire links to Settings → Speech with the appropriate direction, derive availability from audio_capabilities, preserve user preferences while showing effective modes, and add boundary tests for unavailable, unknown, and mixed-provider states. No provider switching or production capability gating is included in these Lab proposals.

## Selected shortcut

Krzysztof selected **More ↗**. Applied to the production component; the shortcut comparison is retired. The provider-availability design remains in Lab for further review.

## Compact language guidance

Default language helper: “Language support varies by model.” Details opens a small overlay containing the engine-specific explanation and change-engine link, without pushing the remaining controls down. Internal design notes stay in this document rather than the settings preview.
