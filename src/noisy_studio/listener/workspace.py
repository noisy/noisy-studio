"""Project and branch of a conversation, derived from the directory it runs in.

There is no project setup: a project is the git repository the session was
started in (a linked worktree belongs to its main repository), and outside
git it is just the directory's name. The branch is read fresh-ish, because a
session can switch it at any time.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

CACHE_SECONDS = 15.0  # /status is polled often; git is not free
GIT_TIMEOUT_SECONDS = 1.0


@dataclass(frozen=True)
class Workspace:
    project: str
    branch: str | None


def _git(cwd: str, *args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", cwd, *args], capture_output=True, text=True,
            timeout=GIT_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def read_workspace(cwd: str, git: Callable[..., str | None] = _git) -> Workspace | None:
    if not cwd:
        return None
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return Workspace(project=Path(cwd).name or cwd, branch=None)
    root = Path(common)
    # A normal checkout's common dir is <repo>/.git; a bare repo has no .git.
    repo = root.parent if root.name == ".git" else root
    return Workspace(project=repo.name.removesuffix(".git"), branch=git(cwd, "branch", "--show-current") or None)


class WorkspaceCache:
    def __init__(self, reader: Callable[[str], Workspace | None] = read_workspace,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._reader = reader
        self._clock = clock
        self._seen: dict[str, tuple[float, Workspace | None]] = {}

    def get(self, cwd: str) -> Workspace | None:
        now = self._clock()
        cached = self._seen.get(cwd)
        if cached and now - cached[0] < CACHE_SECONDS:
            return cached[1]
        workspace = self._reader(cwd)
        self._seen[cwd] = (now, workspace)
        return workspace
