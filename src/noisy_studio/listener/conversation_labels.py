"""Display names are never routing keys or filesystem paths (#107)."""

import re

UNNAMED_CONVERSATION = "New conversation"


def conversation_title(title: str) -> str:
    """Return a safe title, or no title when directory syntax is present.

    Reject separators even inside prose: a generated title can quote a path.
    Being conservative also excludes slash-separated names such as CI/CD.
    Never use a basename: that can still expose a private directory name.
    """
    text = title.strip()
    if "/" in text or "\\" in text or re.search(r"\b[A-Za-z]:", text):
        return ""
    return text


def conversation_label(title: str) -> str:
    return conversation_title(title) or UNNAMED_CONVERSATION
