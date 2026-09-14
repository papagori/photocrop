"""Discover inputs without following directory links or collecting exports."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import tr

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp'}
OUTPUT_DIR = 'PhotoCrop_Export'
# Keep legacy export folders out of recursive input discovery. Existing folders
# are intentionally left untouched; only new exports use OUTPUT_DIR.
EXCLUDED_OUTPUT_DIRS = frozenset({OUTPUT_DIR.casefold(), '4x3_cropped'.casefold()})


@dataclass
class Discovery:
    files: list[Path] = field(default_factory=list)
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def discover(paths, recursive=False, existing=(), language='en'):
    result = Discovery()
    seen = {os.path.normcase(str(Path(p).resolve())) for p in existing}

    def add(path):
        key = os.path.normcase(str(path.resolve()))
        if path.suffix.lower() not in EXTENSIONS or key in seen:
            result.skipped += 1
        else:
            seen.add(key)
            result.files.append(path.resolve())

    for raw in paths:
        path = Path(raw)
        try:
            if path.is_file():
                add(path)
            elif path.is_dir():
                if path.name.casefold() in EXCLUDED_OUTPUT_DIRS:
                    result.skipped += 1
                    continue
                for base, dirs, files in os.walk(path, onerror=lambda e: result.errors.append(str(e))):
                    dirs[:] = sorted(d for d in dirs if recursive and d.casefold() not in EXCLUDED_OUTPUT_DIRS
                                     and not (Path(base) / d).is_symlink())
                    for name in sorted(files):
                        add(Path(base) / name)
            else:
                result.errors.append(tr('error_not_found', language, path=path))
        except OSError as exc:
            result.errors.append(f'{path}: {exc}')
    return result
