"""One session, one identity.

A Claude session arrives at the daemon under two different names depending
on which producer got there first: the hooks send its `session_id`, while
the harness adapter used to prefer its `transcript_path`. Nothing
reconciled the two, so a single session was registered twice - and every
store keyed by identity (the voice ledger, the character buckets, the
conversation tabs) grew two entries for one human.

The cost was not theoretical. A duplicate in the voice ledger guaranteed a
drop on the next load, which is how a viewer's voice changed mid-sentence;
and a path-keyed conversation with no title rendered its key as the tab
label, which is how an absolute filesystem path ended up on screen during
a livestream.

The session id is canonical: it is stable, opaque, and safe to display.
The transcript path is derived - it can move, and it leaks a directory
layout - so it is only ever an alias. See issue #107.
"""

from pathlib import PurePosixPath

TRANSCRIPT_SUFFIX = ".jsonl"


def canonical_identity(name: str) -> str:
    """The session id behind `name`, or `name` unchanged.

    A transcript path is `<dir>/<session_id>.jsonl`, so the stem IS the
    session id - no lookup table, no guessing, and it keeps working for
    sessions this daemon has never seen. Anything that is not a transcript
    path is returned untouched, so agent names like "chat" survive.
    """
    text = str(name).strip()
    if not text.lower().endswith(TRANSCRIPT_SUFFIX):
        return text
    stem = PurePosixPath(text.replace("\\", "/")).stem
    # A hidden file ("/.jsonl") keeps its dot in the stem, so the suffix was
    # never stripped and there is no session name here. Returning the
    # original is always safe, where inventing a key is not.
    if not stem or stem.startswith("."):
        return text
    return stem


def is_transcript_path(name: str) -> bool:
    return str(name).strip().lower().endswith(TRANSCRIPT_SUFFIX)


def fold_by_identity(entries: dict[str, str]) -> tuple[dict[str, str], int]:
    """Collapse path-keyed entries onto their session-id twin.

    Returns the folded mapping and how many entries were folded away. When
    both spellings exist the SESSION ID wins: it is the one the hooks have
    been writing all along, so it is the one a returning session will ask
    for. A path-only entry is renamed rather than dropped, so nobody loses
    a voice they have already been heard in.
    """
    folded: dict[str, str] = {}
    collapsed = 0
    # Session ids first, so a later path entry can never overwrite them.
    for name, value in entries.items():
        if not is_transcript_path(name):
            folded[name] = value
    for name, value in entries.items():
        if not is_transcript_path(name):
            continue
        key = canonical_identity(name)
        if key in folded:
            collapsed += 1
            continue
        folded[key] = value
        collapsed += 1
    return folded, collapsed
