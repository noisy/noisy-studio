from pathlib import Path

from noisy_studio.config_dir import CONFIG_DIR


def test_tests_never_touch_a_real_config_folder():
    real = {Path.home() / ".config" / "noisy-studio", Path.home() / ".config" / "noisy-studio-dev"}

    assert CONFIG_DIR.resolve() not in {path.resolve() for path in real}
