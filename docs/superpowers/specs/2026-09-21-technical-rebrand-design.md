# Independent V3 technical rebrand

Approved by Krzysztof on 2026-09-21, then revised during implementation: **V3 may break compatibility. Provide an agent-friendly upgrade guide instead of maintaining old-name aliases or automatic migrations.** This supersedes the initial compatibility proposal and its first implementation commit.

Make noisy-studio/noisy_studio/NOISY_STUDIO canonical throughout source, integrations, packaging, scripts, tests and current documentation. Independently inspect current main; do not apply conflicted PR #90, which includes obsolete Docker work. Work locally on main with coherent verified commits; do not push or publish.

No Python alias package, legacy CLI/environment fallback, old MCP-name support, or automatic config/profile migration remains. New app bundle IDs and Electron profiles use Studio names; signed macOS upgrade/permissions require release validation. Keep the existing engine identity, ports and website domain. Data is not deleted or silently merged. Existing installations follow docs/rebranding.md to back up and explicitly copy their correct store, or select it with the new environment override. Dev/production must stay isolated.

The active dev instance must retain its current data throughout development. Vite defaults to 7765 so renaming an override cannot reconnect to the old default port. Do not restart until new code, package and frozen protocol checks pass. Use the postponable 60-second shutdown and explicitly select the existing dev store for the first renamed launch. Current host integration configuration is not edited while on stream; reconnection to renamed MCP tools is a documented upgrade step.

Validation covers Python unit/harness contracts, actual distribution/build metadata and CLI names, frozen MCP/hook protocols, frontend and desktop checks/builds, source residue audit, and live dev UI/history/microphone/voice. Old spellings may remain in the upgrade guide, git history and historical media; every active implementation reference must be removed. Do not alter unrelated untracked files or the user's checkout name.
