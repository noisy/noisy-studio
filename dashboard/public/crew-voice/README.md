# crew-voice

Voice clips for the agent lines in `Synthetic Screenshots/Crew`
(`dashboard/src/components/CompanionCrew.stories.ts`).

Generated with the product's own TTS path: the xAI/Grok batch TTS API
(`POST https://api.x.ai/v1/tts`, the same endpoint
`src/noisy_coding/providers/grok.py` calls), using the same voice ids the
daemon speaks with. So these are the real agent voices, not stand-ins.

| file | voice | line |
|---|---|---|
| `lux-1.mp3`  | lux  | "Green! Ready to promote." |
| `lux-2.mp3`  | lux  | "on it!" |
| `rex-1.mp3`  | rex  | "Last week's PR - finally approved!!!" |
| `luna-1.mp3` | luna | "Alarm went off! It was the courier." |
| `luna-2.mp3` | luna | "Package is big - probably the printer." |

Only the agents have audio. The user lines are silent, the way the product
behaves - you hear the agents, not yourself.

Synthesis parameters: `language: "en"`, `speed: 1.1`. Re-encoded to mono
64 kbps mp3; each clip is under 22 KB.

They live in `public/` rather than beside the story because the dashboard's
tsconfig has no `vite/client` types, so importing an `.mp3` from TypeScript
would not type-check. `public/` is served at the root by both Vite and
Storybook - the same way `voiceSprites.ts` reaches `/avatars.png`.
