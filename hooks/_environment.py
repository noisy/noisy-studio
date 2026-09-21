"""Load the shared stdlib compatibility boundary for standalone source hooks."""
import sys
from pathlib import Path

# Source hooks also run with plain Python; frozen hooks import the bundled package.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from noisy_coding.environment import get, setdefault
