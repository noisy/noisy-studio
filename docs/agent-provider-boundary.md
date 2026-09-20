# Agent provider boundary

Core incoming speech uses `harness/provider.py`: `Registration`, `Speech`,
`Receipt`, `Availability`, `ProviderCapabilities` and the `Provider` protocol.
Lifecycle events use `Event` and `Observation`. None requires hook output,
listener IDs, socket frames, or agent API methods. `AgentProvider` composes a
private delivery implementation; Claude and Codex each have one provider.

`AgentProviders` resolves legacy `claude-hooks`/`codex-hooks` names to the same
`claude`/`codex` objects. Saved conversation provider names migrate without
changing their keys, aliases, character settings or outgoing speech identity.
Unregistered conversations cannot borrow another conversation's connection.
Participant registration cannot overwrite the parent's connection.

The core retains pending speech, stamps its recipient when recording begins,
and submits outside its state lock. Receipts preserve the original utterance
and conversation IDs. Queued, sent, accepted, unavailable, rejected and uncertain
are separate from confirmed. Only a matching confirmed receipt retires pending
speech through the generic receipt path. Providers must not blindly resend an
uncertain attempt; a future push implementation must persist attempt state
before I/O and define its restart policy.

Current hook delivery remains a pull implementation: submission leaves speech
queued, and a valid hook collects it through the compatibility gateway. Existing
hook delivery wording and behavior remain unchanged in #119. It does not claim
a model-read confirmation. `hook_gateway.py` owns HTTP hook replies and prevents
hook pickup for providers that do not grant it. `hook_runtime.py` owns polling
lease/readiness rules. The existing registry lease methods and saved listener
field are compatibility adapters, not requirements of the provider contract.
`hook_contract.py` owns output formatting and hook-specific interpretation fields;
legacy imports from `base.py` remain available to existing adapters.

Generic contract tests use a fake push implementation. Hook-specific tests live
in `test_hook_contract.py`, adapter tests, and the real hook-script integration
suite. Socket activation and durable uncertain-send handling belong to #120.
