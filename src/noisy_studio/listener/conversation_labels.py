"""Display names are never routing keys or filesystem paths (#107)."""

import re

UNNAMED_CONVERSATION = "New conversation"


def conversation_title(title: str, *identities: str) -> str:
    """Return a safe title, or no title when directory syntax is present.

    Reject separators even inside prose: a generated title can quote a path.
    Being conservative also excludes slash-separated names such as CI/CD.
    Never use a basename: that can still expose a private directory name.
    """
    text = title.strip()
    if "/" in text or "\\" in text or re.search(r"\b[A-Za-z]:", text):
        return ""
    # Reject familiar opaque IDs even when an integration supplied one as a title.
    if re.fullmatch(r"[0-9a-fA-F]{8,}", text) or re.fullmatch(
        r"(?:[A-Za-z][\w.-]*[:_-])*[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", text
    ):
        return ""
    for identity in identities:
        if identity and (text == identity or (
            len(text) >= 8 and (identity.startswith(text) or identity.endswith(text))
        )):
            return ""
    return text


def conversation_label(title: str, *identities: str) -> str:
    return conversation_title(title, *identities) or UNNAMED_CONVERSATION
