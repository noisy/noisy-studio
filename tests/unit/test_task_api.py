from types import SimpleNamespace

import pytest

from noisy_studio.listener.task_api import handle_task_request
from noisy_studio.listener.task_progress import TaskProgressStore


@pytest.fixture
def state(tmp_path):
    return SimpleNamespace(
        agents={"thread-1": 100, "thread-2": 100},
        task_progress=TaskProgressStore(tmp_path / "tasks.json"),
    )


def test_api_rejects_unknown_conversation_instead_of_creating_a_tab(state):
    with pytest.raises(ValueError, match="registered canonical"):
        handle_task_request(state, "/task-report", {"agent": "thread-3", "report": {}})


def test_report_and_own_list_do_not_include_other_threads(state):
    for agent, task in [("thread-1", "task-1"), ("thread-2", "task-2")]:
        handle_task_request(
            state,
            "/task-report",
            {
                "agent": agent,
                "report": {
                    "task_id": task,
                    "title": "Prepare design",
                    "state": "working",
                    "revision": 1,
                },
            },
        )

    result = handle_task_request(state, "/task-list", {"agent": "thread-1"})

    assert list(result["threads"]) == ["thread-1"]
    assert list(result["threads"]["thread-1"]) == ["task-1"]


def test_report_request_cannot_smuggle_human_approval(state):
    with pytest.raises(ValueError, match="Unknown report request"):
        handle_task_request(
            state,
            "/task-report",
            {"agent": "thread-1", "report": {}, "action": "approve"},
        )
