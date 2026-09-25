# Approved Stage integration

Promote the approved Lab design into a shared Stage component and a live dashboard adapter. Keep App mounted so its existing push-to-talk handling remains active. Stage fills app content, never enters OS fullscreen, and exits through Back or Escape; exit releases any held PTT lease. Keep restart controls visible above Stage.

Read only existing daemon snapshots. All open conversations appear, including offline tabs. Match caption to the exact currently playing utterance; only played/current agent speech enters the shared transcript. Use actual utterance speaker/voice for subagent attribution. No facilitation, broadcast, or conversation routing changes. Local portrait focus is visual only.

Persist hidden participant IDs, heads/caption/transcript choice, and persona-name/conversation-title mode in localStorage, with validation and safe defaults. Display names use existing identity protections. Preserve all Lab stories and their URLs.

Implementation: promote visual component; add model/preferences and regression coverage; connect App with adapter tests; run full dashboard suite and build. No live config/restart changes in this worktree.
