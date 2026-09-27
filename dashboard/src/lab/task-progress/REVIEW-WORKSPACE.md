# Review workspace exploration (#172)

Prototype only: actual App against Storybook's fictional daemon fixture. No production changes, audio capture, message delivery or approval routing.

The sidebar has two sections. **Ready for review** gathers explicit review targets across all work. **Work by thread** preserves the manager conversation with five delegated work items, alongside two solo conversations. Realistic long thread titles have two-line truncation and full text available via title attributes; work titles use one line. Status and task bars refer to work items, never elapsed time. Review of delegated work retains its parent thread as the feedback recipient.

The current alternatives all use bounded full-width headers, replacing floating controls:

- Compact Header: 88px at desktop width, inline controls and transcript preview.
- Conversation Ribbon: 98px, controls above a one-line conversation ribbon.
- Companion Header: 84px, compact conversation bubble with stacked mode controls.

Each includes recipient avatar/thread title, PTT or Auto state, feedback preview, deliberate approval, back and an accessible external-link icon. Longer transcript content opens a separate bounded drawer; it cannot grow the header. Narrow screens use a 120px header.

PTT pointer/Space hold-release produces synthetic text. Auto explicitly names the main thread and its button simulates feedback. Opening a review is not approving it. Approval requires confirmation and provides Undo in this demo.

The artifact is static local srcdoc inside a sandboxed iframe with no scripts or privileges. Cannot Embed demonstrates a separate-tab fallback without bypassing browser embedding policies. Review links are local Storybook fixtures only. Live URL policy, recipient routing and agent reporting belong to follow-up implementation after design approval.
