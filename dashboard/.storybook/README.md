# Storybook conventions

Published from `main` at <https://noisystudio.ai/storybook/> as part of the
website's Pages deployment. Its title carries the commit it was built from.

## Four sections, and only four

| section | what belongs there |
|---|---|
| `Dashboard/` | the main window |
| `Widget/` | the companion widget |
| `Website/` | marketing and website components, and the synthetic-screenshot rigs that produce site assets |
| `Lab/` | proofs of concept, option boards, proposals |

**Nothing sits at the root.** A story with no section is a story nobody
finds again.

## Naming

**`Section/Component`, and the component is the file name.** Not a
description of it, not a title-cased phrase - the identifier, in PascalCase,
exactly as the file is called. `Dashboard/AgentTabs` lives in
`AgentTabs.stories.ts`.

That rule exists so the sidebar and the filesystem answer the same question,
and it is cheap to assert: every title currently matches its file name, and
a test can keep it that way.

**States are stories inside a file, not separate titles.** "Listening",
"Empty", "Error" are exports. A second top-level entry for a state splits
one component across two places in the sidebar.

**No annotations in titles** - no `(proposal)`, no `Concepts`, no em dashes.
If it is a proposal, its section is `Lab/`; saying so twice is noise.

## Lab is a waiting room, not an attic

When an agent is asked for "a few options", the variants go to `Lab/` -
never beside the canonical component, where they get mistaken for the real
thing.

A `Lab/` story has exactly two futures: **promoted**, meaning its winner
becomes a state in the component's canonical story, or **deleted**. It does
not live there forever. The `dashboard-design-language` skill has said this
for a while; it was not happening, which is how 43 stories ended up with
four naming styles and two ungrouped entries at the root.

**Delete stories for things that no longer exist.** A story for a deleted
component is worse than no story: it is a reference that lies.
