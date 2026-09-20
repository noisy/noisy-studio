# Git quality gates implementation plan

Issue #127. Work in an isolated worktree; user requested a hooks/CI-only PR and
explicitly deferred the repository-wide reformat until other PRs have merged.

## Design

Use pre-commit staged-file isolation, Ruff for Python, and ESLint/Prettier for web
sources. Share commands between hooks and CI. Auto-fixes stop for review/restaging.
A temporary exact-content baseline exempts unchanged legacy source from default
style checks. Changed/new files and explicit file arguments get normal checks;
tests/builds are never exempt. Remove the baseline in the final formatting PR.

## Work

- [x] Measure suites: Python ~49s (including integrations ~18s), dashboard ~10s.
- [x] Keep relevant tests on commit, full snapshot rechecks/builds on push.
- [x] Configure reproducible dependencies, hooks, CI and release/deployment gates.
- [x] Preserve partially staged edits and cover fixes/failures with disposable repos.
- [x] Remove all application-source reformatting from the PR.
- [x] Retain only targeted stale integration identity expectations required to run that suite.
- [ ] Verify the revised baseline, hooks and CI, then update PR #130.

The standalone recorder tool's obsolete scenario test is outside this PR; keep
that suite out of the newly shared commands rather than modifying unrelated code.
No formatting PR is created yet: its baseline would become stale as other work merges.
