"""Resolve bundled resources in source and PyInstaller-frozen builds."""
import sys
from pathlib import Path


def resource_path(relative_path):
    bundle_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return bundle_root / relative_path
