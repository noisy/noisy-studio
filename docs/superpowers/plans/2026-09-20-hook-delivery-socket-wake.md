# Hook delivery with socket wake-up

Approved direction: hooks alone consume speech; sockets carry a short wake signal
only when speech remains queued. Restore the existing delivery meaning (handed to
the hook), remove model receipt instructions/IDs/tool exposure from normal use.

- Add a provider `wake(conversation)` operation, returning requested/pending/
  unavailable/uncertain without treating a wake request as speech delivery.
- Compose Claude hook delivery with a private wake controller. Reuse registered
  endpoint validation and bounded socket writes. Schedule after the existing
  continuation grace plus a short pickup allowance. Never send speech on socket.
- Persist control requests before I/O. Match UserPromptSubmit to the exact stored
  wake and canonical session. Drain the existing queue in that hook; block an
  empty/duplicate wake harmlessly. Preserve late controls across daemon restart.
- Keep journal claims and the core's atomic queue drain; finalize only actual hook
  pickups durably, so delivered speech is not restored after restart.
- Verify idle/busy/normal hook pickup, cancellation, empty late wake, grouped
  speech, wrong-session wake and restart. Run real isolated Claude sessions and
  inspect delivered cards plus reply, with no model receipt tool.
- Commit, merge to main and deploy only after resolving the shared checkout's
  unexpected branch change. No public push or issue closure.

The socket wake has a short private control token; actual voice content has no
receipt IDs or acknowledgement instructions. A host-held wake remains pending,
not falsely delivered. No blind resend of speech or implicit direct-socket path.
