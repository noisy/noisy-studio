"""Environment compatibility at the boundary; new Studio names take precedence."""
import os

STUDIO_PREFIX = "NOISY_STUDIO_"
LEGACY_PREFIX = "NOISY_CODING_"


def get(name, default=None):
    if name.startswith((STUDIO_PREFIX, LEGACY_PREFIX)):
        suffix = name.removeprefix(STUDIO_PREFIX).removeprefix(LEGACY_PREFIX)
        canonical = STUDIO_PREFIX + suffix
        if canonical in os.environ:
            return os.environ[canonical]
        return os.environ.get(LEGACY_PREFIX + suffix, default)
    return os.environ.get(name, default)


def setdefault(name, default):
    value = get(name)
    if value is None:
        os.environ[name] = default
        return default
    return value
