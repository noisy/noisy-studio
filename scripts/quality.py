#!/usr/bin/env python3
"""Shared, check-only-by-default quality commands for Git hooks and CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WEB_CODE = {".js", ".mjs", ".cjs", ".ts", ".vue"}
WEB_FORMAT = WEB_CODE | {".css", ".html", ".json", ".yaml", ".yml"}
GENERATED_PARTS = {"node_modules", "dist", "build", "storybook-static", ".venv"}


def run(*command: str) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def source_files(filenames: list[str]) -> list[str]:
    if not filenames:
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        filenames = tracked.decode().split("\0")
    return [
        name
        for name in filenames
        if name
        and not Path(name).is_absolute()
        and ".." not in Path(name).parts
        and not GENERATED_PARTS.intersection(Path(name).parts)
        and Path(name).name != "package-lock.json"
        and (ROOT / name).is_file()
        and not (ROOT / name).is_symlink()
    ]


def style(
    operation: str, fix: bool, filenames: list[str], *, all_files: bool = False
) -> None:
    files = source_files(filenames)
    # Temporary adoption baseline: existing source can wait for the coordinated
    # formatting PR. A single byte changed means this exemption no longer applies.
    baseline_path = ROOT / ".quality-baseline.json"
    if not filenames and not fix and not all_files and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text())["files"]
        checked = [
            name
            for name in files
            if baseline.get(name)
            != hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        ]
        print(
            f"Legacy style baseline: {len(files) - len(checked)} unchanged files deferred; changed/new files are checked.",
            flush=True,
        )
        files = checked
    python = [name for name in files if Path(name).suffix == ".py"]
    extensions = WEB_CODE if operation == "lint" else WEB_FORMAT
    web = [name for name in files if Path(name).suffix in extensions]
    if python:
        args = (
            ["check", *(["--fix"] if fix else [])]
            if operation == "lint"
            else ["format", *([] if fix else ["--check"])]
        )
        run("uv", "run", "--frozen", "ruff", *args, "--", *python)
    if web:
        command = operation + (":fix" if fix else "")
        run("npm", "run", command, "--", "--", *web)


def tests(suite: str) -> None:
    if suite in {"python", "all"}:
        run(
            "uv",
            "run",
            "--frozen",
            "pytest",
            "tests/unit",
            "tests/harness",
            "tests/integration",
            "-q",
        )
    if suite in {"web", "all"}:
        run("npm", "test", "--prefix", "dashboard")
        run("npm", "test", "--prefix", "website")
        run("npm", "test", "--prefix", "desktop")


def build() -> None:
    run("npm", "run", "typecheck:analytics", "--prefix", "website")
    run("npm", "run", "build", "--prefix", "website")
    run("npm", "run", "build", "--prefix", "dashboard")


def push() -> None:
    # pre-commit supplies the tip being pushed, including pushes spanning many
    # commits. Refuse testing a different checkout or uncommitted tracked edits.
    tip = os.environ.get("PRE_COMMIT_TO_REF")
    if not tip and os.environ.get("PRE_COMMIT_LOCAL_BRANCH"):
        tip = subprocess.check_output(
            ["git", "rev-parse", os.environ["PRE_COMMIT_LOCAL_BRANCH"] + "^{commit}"],
            cwd=ROOT,
            text=True,
        ).strip()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if tip and tip != head:
        raise SystemExit(
            "Check out the branch tip being pushed before running pre-push checks."
        )
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise SystemExit(
            "Commit or stash nonignored changes before pushing so checks test the committed revision."
        )
    style("lint", False, [])
    style("format", False, [])
    tests("all")
    build()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["lint", "format", "test", "build", "push"])
    parser.add_argument("--fix", action="store_true")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_files",
        help="Check legacy sources too, ignoring the temporary baseline",
    )
    parser.add_argument("--suite", choices=["python", "web", "all"], default="all")
    parser.add_argument("files", nargs="*")
    args = parser.parse_intermixed_args()
    if args.command in {"lint", "format"}:
        style(args.command, args.fix, args.files, all_files=args.all_files)
    elif args.command == "test":
        tests(args.suite)
    elif args.command == "build":
        build()
    else:
        push()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
