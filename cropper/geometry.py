"""Crop geometry and direct output sizing, independent of Pillow and Qt."""
from .settings import ProcessingOptions


def crop_box(width, height, ratio=(4, 3)):
    """Return the largest centered integer-pixel box near the requested ratio.

    One source dimension is retained in full and the other is rounded to the
    nearest pixel. Thus 6000 × 4000 becomes 5333 × 4000 at 4:3.
    """
    if width < 1 or height < 1:
        raise ValueError('Image dimensions must be positive.')
    if ratio is None:
        return 0, 0, width, height
    a, b = ratio
    if a < 1 or b < 1:
        raise ValueError('Aspect ratio must be positive.')
    if height > width:
        a, b = b, a
    if width * b > height * a:
        crop_width = min(width, max(1, round(height * a / b)))
        crop_height = height
    else:
        crop_width = width
        crop_height = min(height, max(1, round(width * b / a)))
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    return left, top, left + crop_width, top + crop_height


def output_size(cropped_size, options: ProcessingOptions, *, portrait=False):
    width, height = cropped_size
    preset = options.output
    if preset.dimensions:
        target = preset.dimensions[::-1] if portrait else preset.dimensions
    elif preset.long_edge:
        edge = preset.long_edge
        if width >= height:
            target = edge, max(1, round(height * edge / width))
        else:
            target = max(1, round(width * edge / height)), edge
    else:
        return cropped_size, False
    blocked = not options.allow_upscaling and (target[0] > width or target[1] > height)
    return (cropped_size if blocked else target), blocked
