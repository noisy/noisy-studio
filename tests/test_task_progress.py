import pytest

from noisy_studio.listener.task_progress import TaskProgressStore, validate_report


@pytest.fixture
def report():
    return {
        "task_id": "task-1",
        "revision": 1,
        "title": "Review audio controls",
        "state": "done",
        "completed": 3,
        "total": 3,
        "role": "Dashboard agent",
        "model": None,
        "review": {"label": "Open preview", "url": "http://localhost:6038/preview"},
    }


def test_retry_preserves_human_approval_and_restart_recovers_it(tmp_path, report):
    path = tmp_path / "tasks.json"
    store = TaskProgressStore(path, clock=lambda: 100)
    store.report("thread-1", report)
    approved = store.review("thread-1", "task-1", 1, "approve")

    retry = store.report("thread-1", report)
    recovered = TaskProgressStore(path).snapshot("thread-1")["threads"]

    assert retry == approved
    assert recovered == {"thread-1": {"task-1": {**approved, "stale": False}}}


def test_new_revision_resets_review_and_rejects_old_approval(tmp_path, report):
    store = TaskProgressStore(tmp_path / "tasks.json")
    store.report("thread-1", report)
    store.review("thread-1", "task-1", 1, "approve")
    newer = store.report("thread-1", {**report, "revision": 2})

    with pytest.raises(ValueError, match="task changed"):
        store.review("thread-1", "task-1", 1, "approve")
    assert newer["review_state"] == "unopened"


def test_opening_approved_artifact_does_not_revoke_approval(tmp_path, report):
    store = TaskProgressStore(tmp_path / "tasks.json")
    store.report("thread-1", report)
    approved = store.review("thread-1", "task-1", 1, "approve")

    assert store.review("thread-1", "task-1", 1, "opened") == approved


def test_thread_scope_prevents_colliding_task_ids_and_unknown_is_not_zero(
    tmp_path, report
):
    store = TaskProgressStore(tmp_path / "tasks.json")
    store.report("thread-1", report)
    second = store.report(
        "thread-2",
        {
            **report,
            "title": "Different work",
            "state": "working",
            "completed": None,
            "total": None,
            "review": None,
        },
    )

    assert store.snapshot("thread-3") == {"threads": {}, "error": None}
    assert store.snapshot("thread-2")["threads"] == {
        "thread-2": {"task-1": {**second, "stale": False}}
    }


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///tmp/private",
        "https://user:password@example.com/a",
        "https://example.com:bad/a",
        "https://example.com/\nfoo",
        "https://example.com\\@other.test",
    ],
)
def test_review_url_rejects_unsafe_or_ambiguous_targets(report, url):
    with pytest.raises(ValueError):
        validate_report({**report, "review": {"label": "Preview", "url": url}})


@pytest.mark.parametrize(
    "fields",
    [
        {"completed": True},
        {"completed": 4},
        {"total": None},
        {"revision": 0},
        {"approved": True},
        {"thread_id": "thread-2"},
    ],
)
def test_reports_reject_false_counts_review_approval_and_routing_fields(report, fields):
    with pytest.raises(ValueError):
        validate_report({**report, **fields})


def test_corrupt_store_is_preserved_and_blocks_writes(tmp_path, report):
    path = tmp_path / "tasks.json"
    path.write_text("broken original content")
    store = TaskProgressStore(path)

    with pytest.raises(ValueError, match="original file was preserved"):
        store.report("thread-1", report)
    assert path.read_text() == "broken original content"


def test_failed_atomic_write_does_not_change_memory_or_previous_snapshot(
    tmp_path, report, monkeypatch
):
    path = tmp_path / "tasks.json"
    store = TaskProgressStore(path)
    store.report("thread-1", report)
    original = store.snapshot()
    original_file = path.read_text()

    def fail_replace(*args):
        raise OSError("disk full")

    monkeypatch.setattr("noisy_studio.listener.task_progress.os.replace", fail_replace)
    with pytest.raises(OSError, match="disk full"):
        store.report("thread-1", {**report, "revision": 2})
    assert (store.snapshot(), path.read_text()) == (original, original_file)


def test_stale_report_is_not_rewritten_or_marked_complete(tmp_path, report):
    now = [100]
    store = TaskProgressStore(tmp_path / "tasks.json", clock=lambda: now[0])
    store.report("thread-1", {**report, "state": "working"})
    now[0] += 1000
    result = store.snapshot()["threads"]["thread-1"]["task-1"]

    assert (result["stale"], result["report"]["state"]) == (True, "working")
