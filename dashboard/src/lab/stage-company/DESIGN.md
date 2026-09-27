# Company Stage design lab

Approved scope: visual prototypes with fictional people; no live agent hierarchy or microphone routing changes.

## Three compositions
- Company portrait: the CEO above four department constellations, each lead surrounded by smaller specialist portraits. Recommended overview.
- Department spotlight: select a department to expand its specialists; the rest remain visible as context.
- On air: a clean company portrait with a caption for marketing captures, without interactive chrome.

The shared component takes an explicit CEO and departments with leads and workers. Every person has a stable ID, name, role and voice avatar. Active speech is an ID, independent of organizational seniority. Existing editorial crop metadata is used unchanged.

## Implementation and verification
1. Add typed fixture cast, reusable portrait, and company composition with responsive department groups.
2. Add three isolated Lab stories. Controls switch the fictional speaker; spotlight buttons only change local layout.
3. Run TypeScript/build checks and a Storybook build. Review wide and narrow layouts visually. Commit the completed design increment.

Reduced motion disables the speaking animation. All names and roles remain real text, department controls are keyboard operable, and mobile layouts stack department groups rather than shrinking portraits into unreadable dots. No backend capability is implied by these fixtures.
