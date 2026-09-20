"""Compatibility boundary for character records and older dashboard requests."""


def canonical_character_traits(values: dict) -> dict:
    canonical = dict(values)
    if "verbosity" not in canonical and "brevity" in canonical:
        canonical["verbosity"] = 100 - int(canonical["brevity"])
    if "talkative" not in canonical and "chatty" in canonical:
        canonical["talkative"] = canonical["chatty"]
    canonical.pop("brevity", None)
    canonical.pop("chatty", None)
    return canonical
