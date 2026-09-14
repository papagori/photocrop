"""EXIF orientation, centered crop, optional single resize, and image export."""
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from .export import export_image, pixels_for_resize
from .geometry import crop_box, output_size
from .i18n import tr
from .settings import ProcessingOptions


@dataclass
class Result:
    source: Path
    output: Path | None = None
    original_size: tuple[int, int] | None = None
    size: tuple[int, int] | None = None
    error: str = ''
    cropped_size: tuple[int, int] | None = None
    upscaling_blocked: bool = False


def process_image(source, options=ProcessingOptions()):
    source = Path(source)
    try:
        with Image.open(source) as original:
            if getattr(original, 'n_frames', 1) > 1:
                raise ValueError(tr('error_multipage', options.language))
            image = ImageOps.exif_transpose(original)
            image.load()
            before = image.size
            box = crop_box(*before, options.effective_ratio)
            exif = image.getexif()
            exif.pop(274, None)
            cropped = image if box == (0, 0, *before) else image.crop(box)
            final_size, blocked = output_size(cropped.size, options, portrait=before[1] > before[0])
            final = cropped
            if final_size != cropped.size:
                # Convert only as required by the selected format, then perform
                # the one and only resize directly with LANCZOS.
                pixels, icc = pixels_for_resize(cropped, options.output_format, options.language)
                final = pixels.resize(final_size, Image.Resampling.LANCZOS, reducing_gap=None)
                final.info = dict(cropped.info)
                if icc:
                    final.info['icc_profile'] = icc
                else:
                    final.info.pop('icc_profile', None)
            # Remove TIFF storage/layout tags, which no longer describe the JPEG.
            for tag in (254, 255, 258, 259, 262, 266, 273, 277, 278, 279, 284,
                        317, 320, 322, 323, 324, 325, 330, 338, 339, 513, 514):
                exif.pop(tag, None)
            for tag, value in ((256, final.width), (257, final.height)):
                if tag in exif:
                    exif[tag] = value
            if 34665 in exif:
                details = exif.get_ifd(34665)
                details[40962], details[40963] = final.size
            output = export_image(final, source, exif, options.output_format, options.language)
            return Result(source, output, before, final.size, cropped_size=cropped.size,
                          upscaling_blocked=blocked)
    except Exception as exc:
        return Result(source, error=f'{type(exc).__name__}: {exc}')
