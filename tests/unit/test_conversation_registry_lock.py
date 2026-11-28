"""Registry changes from other threads wait for a save in progress.

Hook, HTTP, hotkey and saver threads share one registry. If a change could
land while a save is copying rows, two saves could also write the same .tmp
at once, and a torn conversations.json loads as an empty registry.
"""

from __future__ import annotations

import json
import threading

from noisy_studio.listener import conversations as conversations_module
from noisy_studio.listener.conversations import ConversationRegistry

WAIT_SECONDS = 0.2


def test_a_change_from_another_thread_waits_until_a_save_has_finished(tmp_path, monkeypatch):
    path = tmp_path / "conversations.json"
    registry = ConversationRegistry(path=path)
    registry.adopt("a", "Alpha", "fake")
    real_dumps = json.dumps
    other_thread: list[threading.Thread] = []
    finished_during_save: list[bool] = []

    def dumps_while_the_hotkey_thread_assigns_a_key(data, *args, **kwargs):
        if not other_thread:  # only the first save; the other thread's own save is real
            other_thread.append(threading.Thread(target=registry.set_talk_key, args=("a", "F13")))
            other_thread[0].start()
            other_thread[0].join(WAIT_SECONDS)
            finished_during_save.append(not other_thread[0].is_alive())
        return real_dumps(data, *args, **kwargs)

    monkeypatch.setattr(conversations_module.json, "dumps", dumps_while_the_hotkey_thread_assigns_a_key)
    registry.hide("a")
    other_thread[0].join()

    assert finished_during_save == [False]
    assert json.loads(path.read_text())["talk_keys"] == {"a": "F13"}
