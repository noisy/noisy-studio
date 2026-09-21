# Freeze the daemon into one binary the app can carry.
#
# The desktop app must not require Python: a user downloads one thing, and
# the engine rides inside it. PyInstaller bundles the interpreter and every
# dependency into a single executable, spawned by the shell on 9765.
#
# Build:  .venv/bin/pyinstaller desktop/daemon.spec --distpath desktop/build/daemon
# Output: desktop/build/daemon/Noisy Studio Engine.app (the shipped engine) and
#         desktop/build/daemon/noisy-studio-daemon/ (the same onedir tree, for local runs)
import json
import sys
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

ROOT = Path.cwd()
APP_VERSION = json.loads((ROOT / "desktop" / "package.json").read_text())["version"]

a = Analysis(
    [str(ROOT / "src" / "noisy_studio" / "listener" / "__main__.py")],
    # Claude hook modules are frozen into the same runtime as the engine.
    pathex=[str(ROOT / "src"), str(ROOT / "hooks")],
    binaries=[],
    datas=[
        # The built dashboard travels with the daemon - it serves these
        # files at /next/, and the app's windows load them from there.
        (str(ROOT / "dashboard" / "dist"), "dashboard/dist"),
    ]
    # The daemon reads its own version from package metadata; without the
    # dist-info the frozen build reports "dev" and the update check is
    # meaningless (#100).
    + copy_metadata("noisy-studio"),
    hiddenimports=[
        # Imported dynamically or through plugin machinery, so the static
        # analysis does not see them.
        "sounddevice",
        "_sounddevice_data",
        "httpx",
        "anyio",
        "certifi",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

# onedir, not onefile: a bundle cannot be a single file, and the onefile
# bootloader unpacks unsigned libraries into a temp dir on every launch -
# slow to start and impossible to notarize (#95).
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="noisy-studio-daemon",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="noisy-studio-daemon",
)

# The engine is its own app bundle, not a bare executable (#98): macOS
# keys permissions (microphone, Input Monitoring) to the code identity
# of the process that asks. A bare PyInstaller binary gets a random ad-hoc
# identifier per build - so the Privacy & Security panel showed a generic
# "exec" icon, and every rebuild would have lost the grant. A bundle with
# a stable identifier and an icon is listed as "Noisy Studio Engine".
# LSUIElement keeps it out of the Dock; the Electron app is the face.
app = BUNDLE(
    coll,
    name="Noisy Studio Engine.app",
    icon=str(ROOT / "desktop" / "build" / "icon.icns"),
    bundle_identifier="pl.noisy.studio.engine",
    info_plist={
        "CFBundleName": "Noisy Studio Engine",
        "CFBundleDisplayName": "Noisy Studio Engine",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "Noisy Studio listens to you so your agents can hear you.",
    },
)
