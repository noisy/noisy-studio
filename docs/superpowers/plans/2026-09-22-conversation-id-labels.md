# Keep conversation IDs out of display titles

Goal: enforce the existing unnamed-conversation policy for unfamiliar MCP integrations and restored data.
Design: shared label validation rejects standalone UUID/hex IDs and known routing keys, aliases, short IDs and substantial prefix/suffix fallbacks. Registration and title events preserve a real existing title when an ID fallback arrives. Persisted invalid titles restore as New conversation without altering routing identities or aliases. Frontend guards receive routing identity as context for older daemon data.

- [x] Verify registration, restored saved titles, real-name preservation and frontend fallbacks.
- [x] Apply shared validation in registry and legacy state, and tab/companion display boundaries.
- [x] Build/check, commit, roll into dev with preserved store, and push.

No ID guessing based on arbitrary prose, no routing identity changes, no new Grok protocol support in this fix.

Validation: 470 Python tests passed (1 skipped), 330 dashboard tests passed, dashboard build passed. Dev restarted through the postponable countdown using the preserved store; current labels pass identity checks and Jabra Link 380 remains selected. Fix pushed to main. The original Grok-specific registration sequence was not captured; synthetic registration/restart cases cover the demonstrated shared-boundary gap.
