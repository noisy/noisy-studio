import json

import pytest

from noisy_studio.harness.base import Capabilities, Event, Interpretation
from noisy_studio.listener.conversations import ConversationRegistry
from noisy_studio.listener.state import ListenerState


@pytest.mark.parametrize("title", [
    "/Users/example/projects/session-1",
    "~/projects/session-1",
    "./projects/session-1",
    "../projects/session-1",
    "projects/session-1",
    r"C:\Users\example\session-1",
    r"\\server\share\session-1",
    "C:session-1",
    "Investigate /Users/example/projects/session-1 today",
])
def test_saved_path_titles_never_become_display_labels(tmp_path, title):
    path = tmp_path / "conversations.json"
    path.write_text(json.dumps({"conversations": [{
        "key": "session-1", "harness": "legacy", "created_at": 1,
        "position": 0, "title": title,
    }]}))

    registry = ConversationRegistry(path=path)
    tab = registry.snapshot()["session-1"]

    assert {field: tab[field] for field in ("label", "title")} == {
        "label": "New conversation", "title": "",
    }


@pytest.mark.parametrize("event_kind", ["session_started", "title_changed"])
def test_path_title_event_preserves_the_existing_human_title(event_kind):
    registry = ConversationRegistry()
    registry.adopt("session-1", "Release review")

    registry.apply("test", Interpretation(
        conversation="session-1",
        events=(Event(event_kind, "session-1", title="/projects/session-1"),),
    ), Capabilities("push", None, "events", True, False))

    assert registry.get("session-1").label() == "Release review"


def test_legacy_path_title_does_not_replace_a_human_title():
    registry = ConversationRegistry()
    registry.adopt("session-1", "Release review")

    registry.adopt("session-1", "/projects/session-1")

    assert registry.get("session-1").label() == "Release review"


def test_legacy_agent_metadata_hides_paths_without_changing_routing_identity():
    state = ListenerState()
    state.register_agent("/projects/session-1")
    state.register_agent("session-2", "/projects/session-2")
    state.register_agent("session-3", "Release review")

    assert {
        "labels": state.agent_labels,
        "meta_labels": {key: value["label"] for key, value in state.agents_meta.items()},
        "active": state.active_agent,
    } == {
        "labels": {"/projects/session-1": "New conversation",
                   "session-2": "New conversation", "session-3": "Release review"},
        "meta_labels": {"/projects/session-1": "New conversation",
                        "session-2": "New conversation", "session-3": "Release review"},
        "active": "/projects/session-1",
    }
