import unittest
from unittest.mock import patch

from PIL import Image, ImageCms

import test_cropper as baseline
from cropper.geometry import crop_box, output_size
from cropper.gui import MainWindow
from cropper.processing import process_image
from cropper.settings import (
    ASPECT_RATIOS, OUTPUT_PRESETS, PRESET_BY_KEY, ProcessingOptions, presets_for_ratio,
)


EXPECTED_SIZES = {
    '1:1': ((2000, 2000), (3000, 3000), (4000, 4000), (5000, 5000), (6000, 6000)),
    '3:2': ((2400, 1600), (3000, 2000), (3600, 2400), (4500, 3000),
            (6000, 4000), (7500, 5000)),
    '4:3': ((2400, 1800), (3200, 2400), (4000, 3000), (4800, 3600),
            (6000, 4500), (8000, 6000)),
    '5:4': ((2500, 2000), (3000, 2400), (4000, 3200), (5000, 4000), (6000, 4800)),
    '16:9': ((1920, 1080), (2560, 1440), (3840, 2160), (5120, 2880), (7680, 4320)),
    '2:1': ((2000, 1000), (3000, 1500), (4000, 2000), (5000, 2500),
            (6000, 3000), (8000, 4000)),
}


class CatalogAndGeometryTests(unittest.TestCase):
    def test_ratio_order_and_strict_dynamic_catalogs(self):
        self.assertEqual(list(ASPECT_RATIOS), ['Original', '1:1', '3:2', '4:3', '5:4', '16:9', '2:1'])
        original = presets_for_ratio('Original')
        self.assertEqual([p.key for p in original],
                         ['original', 'edge_2000', 'edge_3000', 'edge_4000',
                          'edge_5000', 'edge_6000', 'edge_8000'])
        for ratio, dimensions in EXPECTED_SIZES.items():
            presets = presets_for_ratio(ratio)
            self.assertEqual(presets[0].key, 'maximum')
            self.assertEqual(tuple(p.dimensions for p in presets[1:]), dimensions)
            a, b = ASPECT_RATIOS[ratio]
            self.assertTrue(all(width * b == height * a for width, height in dimensions))

    def test_maximum_crop_examples_and_portrait_inversion(self):
        for size, ratio, expected in (
            ((6000, 4000), (4, 3), (5333, 4000)),
            ((6000, 4000), (16, 9), (6000, 3375)),
            ((4000, 6000), (4, 3), (4000, 5333)),
            ((4000, 6000), (16, 9), (3375, 6000)),
        ):
            left, top, right, bottom = crop_box(*size, ratio)
            self.assertEqual((right - left, bottom - top), expected)
            self.assertLessEqual(abs(left - (size[0] - right)), 1)
            self.assertLessEqual(abs(top - (size[1] - bottom)), 1)

    def test_output_targets_and_no_upscaling(self):
        preset = PRESET_BY_KEY['exact_4000_3000']
        options = ProcessingOptions((4, 3), preset)
        self.assertEqual(output_size((5333, 4000), options), ((4000, 3000), False))
        self.assertEqual(output_size((3000, 2250), options), ((3000, 2250), True))
        allowed = ProcessingOptions((4, 3), preset, True)
        self.assertEqual(output_size((3000, 2250), allowed), ((4000, 3000), False))
        self.assertEqual(output_size((2250, 3000), allowed, portrait=True), ((3000, 4000), False))

    def test_original_ratio_never_crops(self):
        self.assertEqual(crop_box(713, 419, None), (0, 0, 713, 419))
        options = ProcessingOptions(None, PRESET_BY_KEY['edge_2000'], True)
        self.assertEqual(output_size((713, 419), options), ((2000, 1175), False))


class ProcessingTests(unittest.TestCase):
    setUp = baseline.ImageTests.setUp
    tearDown = baseline.ImageTests.tearDown
    make = baseline.ImageTests.make

    def test_maximum_resolution_only_crops(self):
        path = self.make('maximum.png', (6000, 4000))
        with patch.object(Image.Image, 'resize', side_effect=AssertionError('Unexpected resize')):
            result = process_image(path, ProcessingOptions((4, 3), PRESET_BY_KEY['maximum']))
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.cropped_size, (5333, 4000))
        self.assertEqual(result.size, (5333, 4000))

    def test_crop_then_one_direct_lanczos_resize(self):
        path = self.make('landscape.png', (3200, 2400))
        original_resize = Image.Image.resize
        calls = []

        def spy(image, size, resample, **kwargs):
            calls.append((image.size, size, resample, kwargs))
            return original_resize(image, size, resample, **kwargs)

        options = ProcessingOptions((4, 3), PRESET_BY_KEY['exact_2400_1800'])
        with patch.object(Image.Image, 'resize', new=spy):
            result = process_image(path, options)
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.size, (2400, 1800))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ((3200, 2400), (2400, 1800), Image.Resampling.LANCZOS))
        self.assertIsNone(calls[0][3]['reducing_gap'])

    def test_upscaling_is_checked_after_crop(self):
        path = self.make('wide.png', (1800, 600))
        preset = PRESET_BY_KEY['exact_2000_2000']
        result = process_image(path, ProcessingOptions((1, 1), preset))
        self.assertEqual(result.cropped_size, (600, 600))
        self.assertEqual(result.size, (600, 600))
        self.assertTrue(result.upscaling_blocked)
        result = process_image(path, ProcessingOptions((1, 1), preset, True))
        self.assertEqual(result.size, (2000, 2000))
        self.assertFalse(result.upscaling_blocked)

    def test_original_long_edge_has_no_crop(self):
        path = self.make('original.png', (713, 419))
        result = process_image(path, ProcessingOptions(None, PRESET_BY_KEY['edge_2000'], True))
        self.assertEqual(result.cropped_size, (713, 419))
        self.assertEqual(result.size, (2000, 1175))

    def test_portrait_exact_size_and_exif_orientation(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[256], exif[257] = 600, 400
        exif[34665] = {40962: 600, 40963: 400}
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        path = self.make('portrait_exif.jpg', (600, 400), exif=exif, icc_profile=profile)
        preset = PRESET_BY_KEY['exact_2400_1600']
        result = process_image(path, ProcessingOptions((3, 2), preset, True))
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.original_size, (400, 600))
        self.assertEqual(result.size, (1600, 2400))
        with Image.open(result.output) as exported:
            self.assertEqual(exported.info['icc_profile'], profile)
            self.assertNotIn(274, exported.getexif())


class SettingsGuiTests(unittest.TestCase):
    setUp = baseline.ImageTests.setUp
    tearDown = baseline.ImageTests.tearDown
    make = baseline.ImageTests.make
    wait_idle = baseline.GuiTests.wait_idle
    setUpClass = classmethod(baseline.GuiTests.setUpClass.__func__)

    def select_output(self, window, key):
        for index in range(window.output_size.count()):
            preset = window.output_size.itemData(index)
            if preset.key == key:
                window.output_size.setCurrentIndex(index)
                return
        self.fail(f'Missing compatible preset: {key}')

    def test_dynamic_menu_preview_and_worker_snapshot(self):
        window = MainWindow()
        window.show()
        self.addCleanup(window.close)
        self.assertEqual(window.aspect.currentText(), '4:3')
        self.assertEqual(window.output_size.currentText(), 'Maximum Resolution — Keep Maximum Pixels')
        self.assertEqual(window.output_size.count(), len(OUTPUT_PRESETS['4:3']))

        window.aspect.setCurrentText('3:2')
        available = {window.output_size.itemData(i).key for i in range(window.output_size.count())}
        self.assertIn('exact_2400_1600', available)
        self.assertNotIn('exact_4000_3000', available)

        path = self.make('portrait.png', (400, 600))
        window.add_paths([path])
        self.wait_idle(window)
        self.assertIn('Source: 400 × 600', window.preview.details.text())
        self.assertIn('Crop: 400 × 600', window.preview.details.text())
        self.assertIn('1600 × 2400', [window.output_size.itemText(i) for i in range(window.output_size.count())])

        self.select_output(window, 'exact_2400_1600')
        self.assertIn('Output: 400 × 600', window.preview.details.text())
        self.assertIn('upscaling avoided', window.preview.details.text())
        window.upscaling.setChecked(True)
        self.assertIn('Output: 1600 × 2400', window.preview.details.text())
        window.process.click()
        self.wait_idle(window)
        with Image.open(path.parent / '4x3_cropped' / 'portrait.jpg') as image:
            self.assertEqual(image.size, (1600, 2400))


if __name__ == '__main__':
    unittest.main()
