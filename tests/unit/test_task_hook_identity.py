import importlib
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("participant", [None, "child-1"])
def test_task_hook_overwrites_both_forged_thread_and_reporter(
    monkeypatch, capsys, participant
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "hooks"))
    flow = importlib.import_module("_hook_flow")
    payload = {
        "tool_name": "mcp__noisy-studio__report_task",
        "tool_input": {
            "task_id": "task-1",
            "agent_id": "forged-thread",
            "reporter_id": "forged-child",
        },
    }

    flow._pre_tool_use(
        payload, {"speech_identity": "thread-1", "participant": participant}
    )

    output = json.loads(capsys.readouterr().out)
    assert output["hookSpecificOutput"]["updatedInput"] == {
        "task_id": "task-1",
        "agent_id": "thread-1",
        "reporter_id": participant,
    }
