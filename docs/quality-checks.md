# Local and CI quality checks

From a permanent checkout, with Python 3.13+, uv and Node 22 available:

```sh
./scripts/setup_quality.sh
```

This installs locked dependencies and both Git hooks. `pre-commit install` keeps
existing hooks in migration mode; a configured `core.hooksPath` is not overwritten.
Resolve that configuration deliberately if installation refuses it. Linked Git
worktrees share hooks: install from a checkout whose `.venv` will remain available,
then run the dependency commands from the setup script in each other worktree.
Do not remove the installing checkout without reinstalling from a retained one.
Git does not install hooks just by cloning; run setup explicitly.

## What runs

- **Commit:** Ruff safe fixes, ESLint fixes and formatting (Ruff/Prettier) on staged
  source files. Python changes run unit, harness and local HTTP/subprocess integration
  tests. Web changes run dashboard, website and desktop tests.
- **Push:** tracked-source lint/format checks with the temporary baseline below, all the above tests, analytics
  typechecking, and website/dashboard production builds. The entire snapshot is
  checked, including earlier commits in the push. Push the checked-out branch tip;
  nonignored changes (including untracked files) must first be committed or stashed.
- **CI:** the same check-only commands for every PR and main push. Release builds
  and version checks use the same resolved SHA as their quality gate. Website
  deployment follows successful main CI using its SHA; manual deployment runs its
  own quality gate. No CI auto-fixes or auto-commits.

Measurements on the development Mac: all Python directories ~49 seconds (including
~18 seconds for the integration directory), dashboard ~10 seconds, website/desktop
~1 second each. None requires deferring an entire test suite;
only typechecking/build work is deferred from commit to push. Reassess the split as
suites grow. All suites still run in CI regardless of changed-file filtering.

The integration directory uses local ephemeral servers, not a live voice daemon.
The harness contract skips fixture scenarios that a particular adapter does not provide. Frozen-engine,
macOS signing/notarization and packaged-app smoke checks remain release-only.
Standalone recorder-tool tests, manual voice benchmarks, the demo backend smoke server, and real microphone/network
checks are not included in commit hooks.

## Temporary adoption baseline — no source reformatting in this PR

The coordinated repository-wide cleanup must wait until competing PRs have merged.
`.quality-baseline.json` records exact SHA-256 hashes of existing sources (including
the narrowly corrected integration fixtures). During default lint/format checks,
only byte-for-byte unchanged legacy files are exempt. A changed or new file gets
normal checks; reverting to the recorded legacy bytes restores its exemption.
Tests and builds are never exempted. This is transitional, not a claim that all
legacy sources pass the newly introduced style rules.

Explicit file arguments and local auto-fix hooks bypass this baseline. No hook or
CI job regenerates it. Do not refresh it merely to hide a new failure. The final
formatting PR should run `format --fix` and `lint --fix`, resolve remaining lint
findings, verify `lint --all` and `format --all`, then remove the baseline file.
Those full-check commands can already report the deferred debt without changing it.

## Auto-fixes and partial staging

Hooks do **not** stage their changes. A fix stops the commit: inspect `git diff`,
stage the intended fixes, and retry. pre-commit temporarily hides unstaged edits;
if restoring them conflicts with a formatter fix, it rolls back the fix and restores
your work. Resolve that file deliberately; never blindly `git add .` to satisfy a
hook. Avoid concurrent edits to the same checkout while a commit hook is running.
Untracked files are not linted until staged. Generated files, dependencies and
package lockfiles are excluded from source formatting; lockfiles are checked by
frozen installs/`npm ci` in CI.

## Shared commands

Run from any working directory using the path to this checkout's script:

```sh
uv run --frozen python scripts/quality.py lint
uv run --frozen python scripts/quality.py format
uv run --frozen python scripts/quality.py lint --fix -- path/to/file.py
uv run --frozen python scripts/quality.py format --fix -- path/to/file.vue
uv run --frozen python scripts/quality.py test --suite python
uv run --frozen python scripts/quality.py test --suite web
uv run --frozen python scripts/quality.py build
uv run --frozen python scripts/quality.py push
```

With no filenames, style commands check tracked supported sources against the adoption baseline. Hooks use
an explicit staged file list. Paths are relative to the repository root. Fixes are
opt-in; unsafe Ruff fixes are not enabled. ESLint uses recommended JS/TS and Vue
essential rules, with documented exceptions for existing dynamic payloads,
CommonJS modules and component naming. Prettier owns line layout.

## Repository settings

After the workflow lands, make `quality / checks` a required PR status in branch
protection/rulesets (confirm its displayed name on the first run), replacing the
old separate Python/dashboard statuses. Workflow files cannot enforce repository
rulesets or prevent an administrator bypass. This change does not alter those
settings automatically.

Implementation and baseline tracked in #127. Claude edit-time formatting is #128
and should reuse these commands, not introduce a second formatting policy.
