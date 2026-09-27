# Talk-first mobile proposals

Design-only Widgetbook screens reuse the native theme and portrait assets. They do not use the microphone, connect to a daemon, or persist settings.

- Portrait cards are the recommended approach for a small crew; the compact roster is an alternative for many conversations.
- Auto routes the simulated listening state to the selected agent; selecting another card changes the recipient. Pause is visible beside the listening status.
- Push to talk uses a deliberate long press on the portrait area. Release produces a local preview confirmation. A separate Details button never records.
- Agent details show a small identity header and conversation, with one return-to-talk action. Advanced controls are deferred.
- Recent combines messages across all agents and links back to individual conversations.

Open the `Talk first · proposals` group. Try both modes, a long press, Details, and Recent. Dark/light and small/large phone viewports are provided by Widgetbook.

Before production, review the design and specify gesture cancellation, microphone permissions, disconnection, accessibility activation and recording transport. Prototype states are synthetic, not a claim that phone microphone transport already exists.
