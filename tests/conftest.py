"""Every test run gets a throwaway config folder.

CONFIG_DIR is resolved at import time and defaults to the installed app's
folder, so this must run before any noisy_studio import: a handler that
saves settings would otherwise overwrite the real app's settings.json.
"""

import os
import tempfile

os.environ["NOISY_STUDIO_CONFIG_DIR"] = tempfile.mkdtemp(prefix="noisy-studio-tests-")
