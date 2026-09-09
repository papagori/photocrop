"""JPEG conversion and exclusive output creation."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms

from .discovery import OUTPUT_DIR


def jpeg_pixels(image):
    icc = image.info.get('icc_profile')
    # Keep the original profile when the pixel color space remains compatible.
    if image.mode in ('RGB', 'L', 'CMYK'):
        return image, icc
    if image.mode in ('I', 'F') or image.mode.startswith('I;16'):
        raise ValueError('16/32-bit image: 8-bit JPEG conversion requires a tone mapping choice.')
    if 'A' in image.getbands() or 'transparency' in image.info:
        rgba = image.convert('RGBA')
        rgb = Image.new('RGB', image.size, 'white')
        rgb.paste(rgba, mask=rgba.getchannel('A'))
        if image.mode == 'LA' and icc:
            # A grayscale profile cannot be attached to RGB pixels.
            rgb = ImageCms.profileToProfile(rgb.convert('L'), ImageCms.ImageCmsProfile(BytesIO(icc)),
                                           ImageCms.createProfile('sRGB'), outputMode='RGB')
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        return rgb, icc
    if image.mode == 'LAB':
        source = ImageCms.ImageCmsProfile(BytesIO(icc)) if icc else ImageCms.createProfile('LAB')
        target = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
        return ImageCms.profileToProfile(image, source, target, outputMode='RGB'), target.tobytes()
    return image.convert('RGB'), icc


def export_jpeg(image, source: Path, exif):
    pixels, icc = jpeg_pixels(image)
    options = dict(quality=100, subsampling=0, optimize=True, exif=exif.tobytes())
    if icc:
        options['icc_profile'] = icc
    if image.info.get('dpi'):
        options['dpi'] = image.info['dpi']
    directory = source.parent / OUTPUT_DIR
    directory.mkdir(exist_ok=True)
    index = 1
    while True:
        suffix = '' if index == 1 else f'_{index}'
        output = directory / f'{source.stem}{suffix}.jpg'
        try:
            stream = output.open('xb')
            break
        except FileExistsError:
            index += 1
    try:
        with stream:
            pixels.save(stream, format='JPEG', **options)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return output
