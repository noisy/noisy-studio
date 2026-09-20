import importlib.util
from pathlib import Path
import subprocess

import pytest

SPEC = importlib.util.spec_from_file_location(
    "quality", Path(__file__).resolve().parents[2] / "scripts/quality.py"
)
quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality)


@pytest.fixture
def repository(tmp_path, monkeypatch):
    monkeypatch.setattr(quality, "ROOT", tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_source_selection_handles_spaces_deleted_files_and_generated_outputs(
    repository,
):
    for name in ["a file.py", "removed.py", "dist/generated.js"]:
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    (repository / "removed.py").unlink()
    (repository / "untracked.py").write_text("value = 2\n")

    assert quality.source_files([]) == ["a file.py"]


@pytest.mark.parametrize(
    "operation,expected",
    [
        ("lint", ("check",)),
        ("format", ("format", "--check")),
    ],
)
def test_check_mode_never_requests_fixes(repository, monkeypatch, operation, expected):
    (repository / "a file.py").write_text("value=1\n")
    commands = []
    monkeypatch.setattr(quality, "run", lambda *args: commands.append(args))

    quality.style(operation, False, ["a file.py"])

    assert commands == [("uv", "run", "--frozen", "ruff", *expected, "--", "a file.py")]


def test_local_lint_requests_safe_fixes_without_unsafe_fixes(repository, monkeypatch):
    (repository / "a.py").write_text("import os\n")
    commands = []
    monkeypatch.setattr(quality, "run", lambda *args: commands.append(args))

    quality.style("lint", True, ["a.py"])

    assert commands == [
        ("uv", "run", "--frozen", "ruff", "check", "--fix", "--", "a.py")
    ]


def test_push_rejects_a_different_revision_before_running_checks(monkeypatch):
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "other-revision")
    monkeypatch.setattr(
        quality.subprocess, "check_output", lambda *args, **kwargs: "head-revision\n"
    )

    with pytest.raises(SystemExit, match="branch tip"):
        quality.push()


def test_push_rejects_uncommitted_tracked_changes(monkeypatch):
    monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)
    answers = iter(["head-revision\n", b" M a.py\n"])
    monkeypatch.setattr(
        quality.subprocess, "check_output", lambda *args, **kwargs: next(answers)
    )

    with pytest.raises(SystemExit, match="Commit or stash"):
        quality.push()


def test_push_stops_on_failing_tests_before_building(monkeypatch):
    monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)
    answers = iter(["head-revision\n", b""])
    monkeypatch.setattr(
        quality.subprocess, "check_output", lambda *args, **kwargs: next(answers)
    )
    monkeypatch.setattr(quality, "style", lambda *args: None)

    def fail_tests(suite):
        raise subprocess.CalledProcessError(1, "tests")

    monkeypatch.setattr(quality, "tests", fail_tests)
    monkeypatch.setattr(
        quality, "build", lambda: pytest.fail("Build ran after failed tests")
    )

    with pytest.raises(subprocess.CalledProcessError):
        quality.push()


@pytest.fixture
def staged_repository(repository):
    import os
    import shutil
    import sys

    project = Path(__file__).resolve().parents[2]
    shutil.copy(project / ".pre-commit-config.yaml", repository)
    (repository / "scripts").mkdir()
    shutil.copy(project / "scripts/quality.py", repository / "scripts")
    environment = {
        **os.environ,
        "VIRTUAL_ENV": sys.prefix,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
    }
    environment.pop("PRE_COMMIT_HOME", None)
    # Keep hook caches isolated too; all configured hooks are local/system.
    environment["PRE_COMMIT_HOME"] = str(repository / ".hook-cache")
    (repository / ".gitignore").write_text(".hook-cache/\n")

    def command(*args):
        return subprocess.run(
            args, cwd=repository, env=environment, text=True, capture_output=True
        )

    (repository / "sample file.py").write_text("value = 1\n\n\nother = 1\n")
    command("git", "add", ".")
    result = command(
        "git",
        "-c",
        "user.name=Hook Test",
        "-c",
        "user.email=hook@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    assert result.returncode == 0, result.stderr
    return repository, command, sys.executable


def test_configured_formatter_preserves_partially_staged_changes(staged_repository):
    repository, command, python = staged_repository
    path = repository / "sample file.py"
    staged = "value=2\n\n\nother = 1\n"
    unstaged = "value=2\n\n\nother = 3\n"
    path.write_text(staged)
    command("git", "add", path.name)
    path.write_text(unstaged)

    result = command(python, "-m", "pre_commit", "run", "format")

    assert {
        "exit": result.returncode,
        "index": command("git", "show", ":sample file.py").stdout,
        "worktree": path.read_text(),
    } == {"exit": 1, "index": staged, "worktree": unstaged}


def test_configured_linter_fixes_locally_then_rejects_unfixable_errors(
    staged_repository,
):
    repository, command, python = staged_repository
    path = repository / "sample file.py"
    original = "import os\n\nvalue = 1\n"
    path.write_text(original)
    command("git", "add", path.name)

    fixed = command(python, "-m", "pre_commit", "run", "safe-lint-fixes")

    assert {
        "exit": fixed.returncode,
        "index": command("git", "show", ":sample file.py").stdout,
        "worktree": path.read_text(),
    } == {"exit": 1, "index": original, "worktree": "\nvalue = 1\n"}

    path.write_text("value = missing_name\n")
    command("git", "add", path.name)
    rejected = command(python, "-m", "pre_commit", "run", "safe-lint-fixes")
    assert rejected.returncode == 1 and "F821" in rejected.stdout


@pytest.mark.parametrize("operation", ["lint", "format"])
def test_baseline_exempts_only_unchanged_legacy_files(
    repository, monkeypatch, operation
):
    import hashlib
    import json

    legacy = "value=1\n"
    for name in ["legacy.py", "edited.py", "new.py"]:
        (repository / name).write_text(legacy)
    digest = hashlib.sha256(legacy.encode()).hexdigest()
    (repository / ".quality-baseline.json").write_text(
        json.dumps({"files": {"legacy.py": digest, "edited.py": digest}})
    )
    (repository / "edited.py").write_text("value=2\n")
    subprocess.run(["git", "add", "*.py"], cwd=repository, check=True)
    commands = []
    monkeypatch.setattr(quality, "run", lambda *args: commands.append(args))

    quality.style(operation, False, [])

    assert commands[0][-3:] == ("--", "edited.py", "new.py")


@pytest.mark.parametrize(
    "explicit,fix,all_files",
    [(True, False, False), (False, True, False), (False, False, True)],
)
def test_explicit_files_fixes_and_full_audits_bypass_baseline(
    repository, monkeypatch, explicit, fix, all_files
):
    import hashlib
    import json

    source = "value=1\n"
    (repository / "legacy.py").write_text(source)
    (repository / ".quality-baseline.json").write_text(
        json.dumps(
            {"files": {"legacy.py": hashlib.sha256(source.encode()).hexdigest()}}
        )
    )
    subprocess.run(["git", "add", "legacy.py"], cwd=repository, check=True)
    commands = []
    monkeypatch.setattr(quality, "run", lambda *args: commands.append(args))

    quality.style("format", fix, ["legacy.py"] if explicit else [], all_files=all_files)

    assert commands[0][-2:] == ("--", "legacy.py")
