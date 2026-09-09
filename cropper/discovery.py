"""Discover inputs without following directory links or collecting exports."""
import os
from dataclasses import dataclass, field
from pathlib import Path

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp'}
OUTPUT_DIR = '4x3_cropped'


@dataclass
class Discovery:
    files: list[Path] = field(default_factory=list)
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def discover(paths, recursive=False, existing=()):
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
                if path.name.casefold() == OUTPUT_DIR.casefold():
                    result.skipped += 1
                    continue
                for base, dirs, files in os.walk(path, onerror=lambda e: result.errors.append(str(e))):
                    dirs[:] = sorted(d for d in dirs if recursive and d.casefold() != OUTPUT_DIR.casefold()
                                     and not (Path(base) / d).is_symlink())
                    for name in sorted(files):
                        add(Path(base) / name)
            else:
                result.errors.append(f'Not found: {path}')
        except OSError as exc:
            result.errors.append(f'{path}: {exc}')
    return result
