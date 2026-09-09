"""Crop geometry and direct output sizing, independent of Pillow and Qt."""
from math import gcd

from .settings import ProcessingOptions


def crop_box(width, height, ratio=(4, 3), *, approximate=False):
    if width < 1 or height < 1:
        raise ValueError('Image dimensions must be positive.')
    if ratio is None:
        return 0, 0, width, height
    a, b = sorted(ratio, reverse=True)
    if b < 1:
        raise ValueError('Aspect ratio must be positive.')
    divisor = gcd(a, b)
    a, b = a // divisor, b // divisor
    if height > width:
        a, b = b, a
    if approximate:
        # Coprime photo presets (2048:1365) otherwise discard excessive pixels
        # or reject small inputs. Keep the nearest integer crop; the single
        # final resampling uses an exact fractional box to avoid distortion.
        if width * b > height * a:
            w, h = min(width, max(1, (height * a + b // 2) // b)), height
        else:
            w, h = width, min(height, max(1, (width * b + a // 2) // a))
    else:
        k = min(width // a, height // b)
        if k < 1:
            raise ValueError('Image too small for an exact integer crop at the selected ratio.')
        w, h = a * k, b * k
    left, top = (width - w) // 2, (height - h) // 2
    return left, top, left + w, top + h


def output_size(cropped_size, options: ProcessingOptions, *, portrait=False):
    width, height = cropped_size
    preset = options.output
    if preset.dimensions:
        target = preset.dimensions[::-1] if portrait else preset.dimensions
    elif preset.long_edge:
        edge = preset.long_edge
        if width >= height:
            target = edge, max(1, (height * edge + width // 2) // width)
        else:
            target = max(1, (width * edge + height // 2) // height), edge
    else:
        return cropped_size, False
    blocked = not options.allow_upscaling and (target[0] > width or target[1] > height)
    return (cropped_size if blocked else target), blocked


def resampling_box(source_size, target_size):
    """Match the rounded output ratio by a subpixel crop, never by stretching."""
    width, height = source_size
    tw, th = target_size
    if width * th > height * tw:
        w = height * tw / th
        left = (width - w) / 2
        return left, 0, left + w, height
    h = width * th / tw
    top = (height - h) / 2
    return 0, top, width, top + h
