# Claude inbox feedback follow-up

**Goal:** Address the two live reports on #120 without inventing receipt evidence.

**Design:** The raw socket transport provides no correlated application receipt.
Use the ticket's bounded-status fallback: persist the write time and move sent
messages to `unknown` after 60 seconds. This is an informational outcome, not
proof of failure. Never resend, recall, or hand these entries to hook delivery.
Preserve the timer across restarts; legacy sent rows without a write time become
unknown immediately because their age cannot be established. Keep actual write
errors distinct as `uncertain`. A future correlated receipt may confirm either.

The content prefix becomes `[VOICE · Noisy Studio transcript]`; app notifications
retain their separate origin. Document Claude's host-controlled peer wrapper.
No documented alternative frame was found in the current messaging reference;
do not claim experimental proof that every possible frame behaves identically.

**Alternatives considered:** Model acknowledgements require a new correlated,
session-bound protocol and are not equivalent to host receipts. Inferring success
from a later hook or spoken answer can confirm the wrong message. Neither is
appropriate as a quick repair. The timeout makes uncertainty bounded but does
not solve application receipt confirmation.

**Implementation:** Work inline in the current main checkout as requested.

- [x] Add write timestamps and atomic sent-to-unknown expiry in the Claude journal;
  call expiry from the socket worker and persist the real completion time.
- [x] Extend core and dashboard states, prohibiting recall and replay of unknown
  entries; add a Storybook example and explain the limitation in message detail.
- [x] Cover send-time deadlines, restart/migration, unrelated states, no replay,
  and state-machine controls. Run the required Python and dashboard checks.
- [x] Commit the status fix, then shorten the prefix and update delivery docs in
  a separate focused commit.
- [x] Rebuild dashboard and gracefully reload the dev instance with the usual
  postponable 60-second countdown. Verify deployed behavior without launching
  more disposable Claude sessions or sending test messages to user sessions.

**Constraints:** Keep canonical identity, permission handling and transport frame
unchanged. No public push/comment/issue closure without the user's instruction.
No private config reads or extra Claude sessions on stream. Test configuration
is isolated from the running instance.
