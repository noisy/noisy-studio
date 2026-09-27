from http.server import ThreadingHTTPServer
import threading

import httpx

from noisy_studio.listener.http_api import _handler_class
from noisy_studio.listener.state import ListenerState
from noisy_studio.listener.task_progress import TaskProgressStore


def test_http_task_report_open_and_approval_use_the_persisted_instance_store(tmp_path):
    state = ListenerState()
    state.register_agent("thread-1", "Bug fixing")
    path = tmp_path / "task-progress.json"
    state.task_progress = TaskProgressStore(path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(state))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            report = {
                "task_id": "task-1",
                "revision": 1,
                "title": "Preview controls",
                "state": "done",
                "review": {
                    "label": "Open preview",
                    "url": "http://localhost:6038/preview",
                },
            }
            submitted = client.post(
                "/task-report", json={"agent": "thread-1", "report": report}
            )
            opened = client.post(
                "/task-review",
                json={
                    "agent": "thread-1",
                    "task_id": "task-1",
                    "revision": 1,
                    "action": "opened",
                },
            )
            approved = client.post(
                "/task-review",
                json={
                    "agent": "thread-1",
                    "task_id": "task-1",
                    "revision": 1,
                    "action": "approve",
                },
            )
            snapshot = client.get("/tasks").json()
            rejected = client.post("/task-report", content="[]")

        assert [
            submitted.status_code,
            opened.json()["task"]["review_state"],
            approved.json()["task"]["review_state"],
            rejected.status_code,
        ] == [200, "opened", "approved", 400]
        assert TaskProgressStore(path).snapshot() == snapshot
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
