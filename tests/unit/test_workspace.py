import subprocess

import pytest

from noisy_studio.harness.claude_hooks.adapter import ClaudeHooks
from noisy_studio.listener.workspace import Workspace, WorkspaceCache, read_workspace


def _repo(path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-q", "--allow-empty", "-m", "init"], check=True)


def test_project_is_the_repository_and_branch_is_current(tmp_path):
    repo = tmp_path / "noisy-studio"
    _repo(repo)
    (repo / "dashboard").mkdir()

    assert read_workspace(str(repo / "dashboard")) == Workspace(project="noisy-studio", branch="main")


def test_a_linked_worktree_belongs_to_its_main_repository(tmp_path):
    repo = tmp_path / "noisy-studio"
    _repo(repo)
    worktree = tmp_path / "elsewhere" / "feature-x"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-b", "feature-x", str(worktree)], check=True)

    assert read_workspace(str(worktree)) == Workspace(project="noisy-studio", branch="feature-x")


def test_outside_git_the_project_is_the_directory_name(tmp_path):
    folder = tmp_path / "Downloads"
    folder.mkdir()

    assert read_workspace(str(folder)) == Workspace(project="Downloads", branch=None)


def test_cache_rereads_only_after_it_expires():
    now = [0.0]
    calls = []
    cache = WorkspaceCache(reader=lambda cwd: calls.append(cwd) or Workspace("p", "b"), clock=lambda: now[0])

    cache.get("/x")
    cache.get("/x")
    now[0] = 20.0
    cache.get("/x")

    assert calls == ["/x", "/x"]


@pytest.mark.parametrize("payload_cwd, expected", [("/work/repo", "/work/repo"), (None, "")])
def test_claude_hook_passes_the_session_directory(payload_cwd, expected):
    adapter = ClaudeHooks(read_text=lambda path: "")
    payload = {"session_id": "s-1", "hook_event_name": "Stop", "cwd": payload_cwd}

    assert adapter.interpret(payload).cwd == expected


def test_registry_keeps_the_directory_across_a_restart(tmp_path):
    from noisy_studio.harness.base import Observation
    from noisy_studio.listener.conversations import ConversationRegistry

    adapter = ClaudeHooks(read_text=lambda path: "")
    registry = ConversationRegistry(path=tmp_path / "c.json")
    registry.apply(adapter.name, adapter.interpret({"session_id": "s-1", "hook_event_name": "Stop", "cwd": "/work/repo"}), adapter.capabilities)
    registry.apply(adapter.name, Observation(conversation="s-1"), adapter.capabilities)  # no cwd: keep it

    assert ConversationRegistry(path=tmp_path / "c.json").get("s-1").cwd == "/work/repo"
