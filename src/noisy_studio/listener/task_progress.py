"""Conversation-scoped work reports and separately recorded human review."""

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlsplit

MAX_TASKS_PER_THREAD = 100
MAX_THREADS = 500
MAX_STORE_BYTES = 8_000_000
STALE_AFTER_SECONDS = 15 * 60
STATES = {"pending", "working", "blocked", "done"}
REPORT_FIELDS = {
    "task_id",
    "revision",
    "title",
    "state",
    "completed",
    "total",
    "participant",
    "role",
    "model",
    "review",
}


def _text(value, field: str, limit: int, optional: bool = False):
    if optional and value is None:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError(
            f"{field} must be non-empty text of at most {limit} characters"
        )
    return value.strip()


def validate_report(report: dict) -> dict:
    if not isinstance(report, dict) or set(report) - REPORT_FIELDS:
        raise ValueError("Unknown task report fields")
    task_id = _text(report.get("task_id"), "task_id", 80)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", task_id):
        raise ValueError("task_id must be a stable identifier")
    revision = report.get("revision")
    if type(revision) is not int or not 1 <= revision <= 2_147_483_647:
        raise ValueError("revision must be a positive integer")
    state = report.get("state")
    if not isinstance(state, str) or state not in STATES:
        raise ValueError("state must be pending, working, blocked or done")
    completed, total = report.get("completed"), report.get("total")
    if completed is not None or total is not None:
        if (
            type(completed) is not int
            or type(total) is not int
            or not 0 <= completed <= total <= 100_000
            or total == 0
        ):
            raise ValueError(
                "completed and total must be bounded task counts, supplied together"
            )
        if state == "done" and completed != total:
            raise ValueError("done tasks must have all reported steps complete")
    review = report.get("review")
    if review is not None:
        if not isinstance(review, dict) or set(review) != {"label", "url"}:
            raise ValueError("review requires only label and url")
        label = _text(review["label"], "review label", 100)
        url = _text(review["url"], "review URL", 2048)
        try:
            parsed = urlsplit(url)
            valid = (
                parsed.scheme in {"http", "https"}
                and parsed.hostname
                and not parsed.username
                and not parsed.password
            )
            parsed.port
        except ValueError:
            valid = False
        if not valid or "\\" in url or any(c.isspace() for c in url):
            raise ValueError(
                "review URL must be an absolute HTTP(S) URL without credentials"
            )
        review = {"label": label, "url": url}
    return {
        "task_id": task_id,
        "revision": revision,
        "title": _text(report.get("title"), "title", 240),
        "state": state,
        "completed": completed,
        "total": total,
        **{
            key: _text(report.get(key), key, 100, optional=True)
            for key in ("participant", "role", "model")
        },
        "review": review,
    }


class TaskProgressStore:
    def __init__(self, path: Path, *, clock=time.time):
        self.path = path
        self._clock = clock
        self._lock = threading.Lock()
        self._threads: dict[str, dict[str, dict]] = {}
        self.load_error: str | None = None
        if path.exists():
            try:
                if path.stat().st_size > MAX_STORE_BYTES:
                    raise ValueError("Task file exceeds size limit")
                data = json.loads(path.read_text())
                if (
                    data.get("version") != 1
                    or not isinstance(data.get("threads"), dict)
                    or len(data["threads"]) > MAX_THREADS
                ):
                    raise ValueError("Unsupported task file")
                for thread, tasks in data["threads"].items():
                    _text(thread, "thread", 240)
                    if not isinstance(tasks, dict) or len(tasks) > MAX_TASKS_PER_THREAD:
                        raise ValueError("Invalid persisted task list")
                    for task_id, entry in tasks.items():
                        report = validate_report(entry["report"])
                        if (
                            task_id != report["task_id"]
                            or type(entry["updated_at"]) not in (float, int)
                            or not math.isfinite(entry["updated_at"])
                        ):
                            raise ValueError("Invalid persisted task")
                        if entry["review_state"] not in {
                            "unopened",
                            "opened",
                            "approved",
                        }:
                            raise ValueError("Invalid review state")
                self._threads = data["threads"]
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                self.load_error = "Saved task progress could not be loaded; the original file was preserved."

    def _persist(self, updated: dict) -> None:
        if self.load_error:
            raise ValueError(self.load_error)
        encoded = json.dumps({"version": 1, "threads": updated}, allow_nan=False)
        if len(encoded.encode()) > MAX_STORE_BYTES:
            raise ValueError("Task progress storage limit reached")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)
        self._threads = updated

    def report(self, thread: str, report: dict, reporter_id: str | None = None) -> dict:
        thread = _text(thread, "thread", 240)
        report = validate_report(report)
        if reporter_id is not None:
            reporter_id = _text(reporter_id, "reporter_id", 100)
            if report["participant"] not in (None, reporter_id):
                raise ValueError("A delegated reporter may only report its own work")
            report["participant"] = reporter_id
        with self._lock:
            if self.load_error:
                raise ValueError(self.load_error)
            existing = self._threads.get(thread, {}).get(report["task_id"])
            if (
                reporter_id
                and existing
                and existing["report"]["participant"] != reporter_id
            ):
                raise ValueError(
                    "A delegated reporter cannot edit another owner's task"
                )
            if existing and report["revision"] <= existing["report"]["revision"]:
                if report == existing["report"]:
                    return deepcopy(existing)
                raise ValueError(
                    "Stale or conflicting revision; read the current task before reporting"
                )
            if thread not in self._threads and len(self._threads) >= MAX_THREADS:
                raise ValueError("Conversation task limit reached")
            if (
                not existing
                and len(self._threads.get(thread, {})) >= MAX_TASKS_PER_THREAD
            ):
                raise ValueError("Task limit reached for this conversation")
            updated = deepcopy(self._threads)
            # Every changed work revision needs fresh review, even when its URL is stable.
            entry = {
                "report": report,
                "updated_at": self._clock(),
                "review_state": "unopened",
            }
            updated.setdefault(thread, {})[report["task_id"]] = entry
            self._persist(updated)
            return deepcopy(entry)

    def review(self, thread: str, task_id: str, revision: int, action: str) -> dict:
        if action not in {"opened", "approve", "undo"}:
            raise ValueError("Invalid human review action")
        with self._lock:
            entry = self._threads.get(thread, {}).get(task_id)
            if not entry or entry["report"]["revision"] != revision:
                raise ValueError(
                    "The task changed; reopen the current result before reviewing"
                )
            if entry["report"]["state"] != "done" or not entry["report"]["review"]:
                raise ValueError(
                    "Only completed work with a review target can be reviewed"
                )
            updated = deepcopy(self._threads)
            target = updated[thread][task_id]
            if action == "approve":
                target["review_state"] = "approved"
            elif action == "undo" or target["review_state"] != "approved":
                target["review_state"] = "opened"
            self._persist(updated)
            return deepcopy(target)

    def snapshot(self, thread: str | None = None) -> dict:
        with self._lock:
            source = (
                self._threads
                if thread is None
                else {thread: self._threads[thread]}
                if thread in self._threads
                else {}
            )
            result = deepcopy(source)
            for tasks in result.values():
                for entry in tasks.values():
                    entry["stale"] = (
                        entry["report"]["state"] != "done"
                        and self._clock() - entry["updated_at"] >= STALE_AFTER_SECONDS
                    )
            return {"threads": result, "error": self.load_error}
