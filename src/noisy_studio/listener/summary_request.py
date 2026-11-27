"""The note that asks an agent to retell its unheard backlog as one message."""
from __future__ import annotations


def summary_request(texts: list[str]) -> str:
    """A [DASHBOARD] note: squash these unheard messages into their net outcome.

    Like squashing commits: the backlog is a history of updates, and many
    of them cancel out (a plan that was later changed, a failure that was
    later fixed). The user wants where things stand now, not the replay.
    """
    backlog = "\n".join(f"{number}. „{text}”" for number, text in enumerate(texts, start=1))
    return (
        f"[DASHBOARD] The user pressed Summarize on {len(texts)} of your spoken "
        "messages they did not hear (oldest first, below). Do not retell them one "
        "by one. Squash them like commits into their net outcome: later messages "
        "supersede earlier ones, so drop whatever was reversed, retried, fixed or "
        "made irrelevant along the way. Keep only what is true now, what changed "
        "for the user, and anything still waiting on their decision. Say it aloud "
        "as ONE short message with the speak tool, starting straight with the "
        f"substance.\n\n{backlog}"
    )
