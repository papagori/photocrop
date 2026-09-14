"""Format-specific pixel conversion and exclusive output creation."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms

from .discovery import OUTPUT_DIR
from .i18n import tr


FORMATS = ('JPEG', 'PNG', 'TGA')
EXTENSIONS = {'JPEG': '.jpg', 'PNG': '.png', 'TGA': '.tga'}


def jpeg_pixels(image, language='en'):
    icc = image.info.get('icc_profile')
    if image.mode in ('RGB', 'L', 'CMYK'):
        return image, icc
    if image.mode in ('I', 'F') or image.mode.startswith('I;16'):
        raise ValueError(tr('error_high_depth_jpeg', language))
    if 'A' in image.getbands() or 'transparency' in image.info:
        rgba = image.convert('RGBA')
        rgb = Image.new('RGB', image.size, 'white')
        rgb.paste(rgba, mask=rgba.getchannel('A'))
        if image.mode == 'LA' and icc:
            rgb = ImageCms.profileToProfile(rgb.convert('L'), ImageCms.ImageCmsProfile(BytesIO(icc)),
                                           ImageCms.createProfile('sRGB'), outputMode='RGB')
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        return rgb, icc
    if image.mode == 'LAB':
        source = ImageCms.ImageCmsProfile(BytesIO(icc)) if icc else ImageCms.createProfile('LAB')
        target = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
        return ImageCms.profileToProfile(image, source, target, outputMode='RGB'), target.tobytes()
    return image.convert('RGB'), icc


def lossless_pixels(image, output_format):
    """Return directly resizable/exportable pixels while retaining alpha."""
    has_alpha = 'A' in image.getbands() or 'transparency' in image.info
    if output_format == 'TGA':
        return image.convert('RGBA' if has_alpha else 'RGB')
    if image.mode == 'P':
        return image.convert('RGBA' if has_alpha else 'RGB')
    if image.mode == '1':
        return image.convert('L')
    return image


def pixels_for_resize(image, output_format, language='en'):
    if output_format == 'JPEG':
        pixels, icc = jpeg_pixels(image, language)
        return pixels, icc
    return lossless_pixels(image, output_format), image.info.get('icc_profile')


def _exclusive_path(source, extension):
    directory = source.parent / OUTPUT_DIR
    directory.mkdir(exist_ok=True)
    index = 1
    while True:
        suffix = '' if index == 1 else f'_{index}'
        output = directory / f'{source.stem}{suffix}{extension}'
        try:
            return output, output.open('xb')
        except FileExistsError:
            index += 1


def export_image(image, source: Path, exif, output_format='JPEG', language='en'):
    output_format = output_format.upper()
    if output_format not in FORMATS:
        raise ValueError(tr('error_unsupported_format', language, format=output_format))
    icc = image.info.get('icc_profile')
    dpi = image.info.get('dpi')
    if output_format == 'JPEG':
        pixels, icc = jpeg_pixels(image, language)
        options = dict(quality=100, subsampling=0, optimize=True, exif=exif.tobytes())
    elif output_format == 'PNG':
        pixels = lossless_pixels(image, output_format)
        options = dict(compress_level=6, optimize=False, exif=exif.tobytes())
    else:
        pixels = lossless_pixels(image, output_format)
        options = {}
    if output_format != 'TGA' and icc:
        options['icc_profile'] = icc
    if output_format != 'TGA' and dpi:
        options['dpi'] = dpi
    output, stream = _exclusive_path(source, EXTENSIONS[output_format])
    try:
        with stream:
            pixels.save(stream, format=output_format, **options)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return output


def export_jpeg(image, source: Path, exif):
    """Backward-compatible wrapper retained for callers of the original API."""
    return export_image(image, source, exif, 'JPEG')
