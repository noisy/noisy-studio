"""Local task API boundary; MCP report identity is injected by host hooks."""

from noisy_studio.listener.identity import canonical_identity


def handle_task_request(state, path: str, body: dict) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Task request must be an object")
    agent = body.get("agent")
    if (
        not isinstance(agent, str)
        or not agent
        or canonical_identity(agent) != agent
        or agent not in state.agents
    ):
        raise ValueError("A registered canonical conversation identity is required")
    store = getattr(state, "task_progress", None)
    if store is None:
        raise ValueError("Task reporting is not initialized")
    if path == "/task-list":
        return store.snapshot(agent)
    if path == "/task-report":
        if set(body) - {"agent", "report", "reporter_id"}:
            raise ValueError("Unknown report request fields")
        return {
            "task": store.report(agent, body.get("report"), body.get("reporter_id"))
        }
    if path == "/task-review":
        if set(body) != {"agent", "task_id", "revision", "action"}:
            raise ValueError("Review requires agent, task_id, revision and action")
        if not isinstance(body["task_id"], str) or type(body["revision"]) is not int:
            raise ValueError("Invalid review task or revision")
        return {
            "task": store.review(
                agent, body["task_id"], body["revision"], body["action"]
            )
        }
    raise ValueError("Unknown task operation")
