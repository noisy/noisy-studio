# Talk-first mobile refinements

These Widgetbook-only proposals use the real mobile theme, portraits and MessageCard. No microphone, transport or persisted settings are involved.

The approved portrait direction now has one card interaction: tap opens the conversation and selects its Auto recipient; hold talks directly without opening anything. The Details buttons and compact roster proposal were removed. Existing functional component stories remain.

Flutter's gesture arena separates a quick tap, a long press and scroll. Once held, dragging 48 logical pixels from the hold origin cancels irreversibly; releasing cannot subsequently send or open the detail. Auto is temporarily suspended during a direct hold and resumes to the explicitly selected recipient afterward. Pause remains visible.

The large detail talk surface is pinned immediately above bottom navigation. A compact PTT/Auto switch shares the app header with a desktop connection icon in both crew and detail views. The crew heading, connection count and repeated tap/hold guidance have been removed. All details retain an explicit recipient. The catalog now contains crew, bottom-talk detail and chronological Recent entry points; superseded upper/middle layouts are removed.

Recent retains the original chronological message-card feed, including user messages and repeated messages from the same agent, with newest messages at the bottom. Each agent bubble has a prominent microphone reply strip. Holding it targets that message's agent, regardless of the selected Auto recipient. User messages have no reply microphone.

Checks protect the risky interactions: hold release never opens detail, dragging cancels, scrolling does not start recording, and Recent reply routing does not use an unrelated selected agent. Live integration still requires design approval and a separate recording transport/accessibility specification.
