"""EXIF-aware exact-ratio cropping, with no pixel resampling."""
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from .export import export_jpeg


def crop_box(width, height):
    a, b = (4, 3) if width >= height else (3, 4)
    k = min(width // a, height // b)
    if k < 1:
        raise ValueError('Image too small for an exact 4:3 or 3:4 integer crop.')
    w, h = a * k, b * k
    left, top = (width - w) // 2, (height - h) // 2
    return left, top, left + w, top + h


@dataclass
class Result:
    source: Path
    output: Path | None = None
    original_size: tuple[int, int] | None = None
    size: tuple[int, int] | None = None
    error: str = ''


def process_image(source):
    source = Path(source)
    try:
        with Image.open(source) as original:
            if getattr(original, 'n_frames', 1) > 1:
                raise ValueError('Multi-page/animated image is not supported; export a single frame first.')
            image = ImageOps.exif_transpose(original)
            image.load()
            before = image.size
            box = crop_box(*before)
            exif = image.getexif()
            exif.pop(274, None)
            cropped = image if box == (0, 0, *before) else image.crop(box)
            # Remove TIFF storage/layout tags, which no longer describe the JPEG.
            for tag in (254, 255, 258, 259, 262, 266, 273, 277, 278, 279, 284,
                        317, 320, 322, 323, 324, 325, 330, 338, 339, 513, 514):
                exif.pop(tag, None)
            for tag, value in ((256, cropped.width), (257, cropped.height)):
                if tag in exif:
                    exif[tag] = value
            if 34665 in exif:
                details = exif.get_ifd(34665)
                details[40962], details[40963] = cropped.size
            output = export_jpeg(cropped, source, exif)
            return Result(source, output, before, cropped.size)
    except Exception as exc:
        return Result(source, error=f'{type(exc).__name__}: {exc}')
