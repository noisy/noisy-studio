# Flat Stage crew design lab

This revision replaces the rejected company hierarchy. There is no CEO, chart, connector line, or reporting hierarchy above the leads. Four equally prominent department leads share the original Stage room, with smaller specialist portraits beneath each.

## Compositions
- Just faces: equal lead portraits and small workers, with plenty of breathing room.
- With caption: the same flat crew plus a single speaking caption.
- Loose constellations: gently staggered department clusters, retaining equal lead sizes.

Working portraits retain full color. Idle portraits are desaturated and dimmed but remain recognizable. Filled/hollow activity markers and explicit Working/Idle text avoid relying on color alone. Speaking independently highlights either a lead or a specialist. All activity is synthetic fixture data.

## Implementation plan and verification
Reuse the existing VoiceAvatar crop mechanism without changing artwork. Keep explicit departments/lead/workers input so future live adapters can provide genuine hierarchy data. Replace old stories instead of presenting rejected options alongside the new ones. Check TypeScript/Vite and Storybook builds, then visually review 1280×720 plus a narrow layout before integration. No microphone routing, daemon, or runtime Stage behavior is changed.
