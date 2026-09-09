import unittest
from unittest.mock import patch

from PIL import Image, ImageCms

import test_cropper as baseline
from cropper.geometry import crop_box, output_size, resampling_box
from cropper.gui import MainWindow
from cropper.processing import process_image
from cropper.settings import ASPECT_RATIOS, PRESETS, PRESET_BY_KEY, ProcessingOptions


class GeometryTests(unittest.TestCase):
    def test_all_ratios_both_orientations_and_square(self):
        for ratio in ASPECT_RATIOS.values():
            for width, height in ((6000, 4000), (4000, 6000), (401, 401)):
                with self.subTest(ratio=ratio, size=(width, height)):
                    left, top, right, bottom = crop_box(width, height, ratio)
                    w, h = right-left, bottom-top
                    if ratio is None:
                        self.assertEqual((left, top, right, bottom), (0, 0, width, height))
                        continue
                    a, b = ratio if width >= height else ratio[::-1]
                    self.assertEqual(w*b, h*a)
                    self.assertLessEqual(abs(left-(width-right)), 1)
                    self.assertLessEqual(abs(top-(height-bottom)), 1)
                    self.assertLessEqual(right, width)
                    self.assertLessEqual(bottom, height)
        self.assertEqual(crop_box(70, 30, (21, 9)), (0, 0, 70, 30))
        self.assertEqual(crop_box(80, 50, (16, 10)), (0, 0, 80, 50))

    def test_requested_long_edge_examples(self):
        preset = PRESET_BY_KEY['edge_4096']
        for ratio, size, expected in (
            ((4, 3), (5332, 3999), (4096, 3072)),
            ((4, 3), (3999, 5332), (3072, 4096)),
            ((16, 9), (6000, 3375), (4096, 2304)),
            ((16, 9), (3375, 6000), (2304, 4096)),
        ):
            self.assertEqual(output_size(size, ProcessingOptions(ratio, preset))[0], expected)

    def test_every_preset_orientation_and_upscaling(self):
        for preset in PRESETS:
            for portrait in (False, True):
                size = (400, 600) if portrait else (600, 400)
                options = ProcessingOptions(output=preset, allow_upscaling=True)
                target, blocked = output_size(size, options, portrait=portrait)
                self.assertFalse(blocked)
                if preset.dimensions:
                    self.assertEqual(target, preset.dimensions[::-1] if portrait else preset.dimensions)
                elif preset.long_edge:
                    self.assertEqual(max(target), preset.long_edge)
                    self.assertLessEqual(abs(min(target)-max(target)*2/3), 0.5)
                else:
                    self.assertEqual(target, size)
                self.assertEqual(output_size(size, ProcessingOptions(output=preset), portrait=portrait)[0], size)

    def test_approximate_presets_keep_maximum_pixels(self):
        for key, size, expected in (
            ('exact_2048_1365', (6000, 4000), (6000, 3999)),
            ('exact_2048_1365', (800, 600), (800, 533)),
            ('exact_5000_3333', (6000, 4000), (6000, 4000)),
        ):
            preset = PRESET_BY_KEY[key]
            x, y, right, bottom = crop_box(*size, preset.ratio, approximate=True)
            self.assertEqual((right-x, bottom-y), expected)
            box = resampling_box(expected, preset.dimensions)
            self.assertAlmostEqual((box[2]-box[0])/(box[3]-box[1]),
                                   preset.dimensions[0]/preset.dimensions[1], places=12)


class ProcessingTests(unittest.TestCase):
    setUp = baseline.ImageTests.setUp
    tearDown = baseline.ImageTests.tearDown
    make = baseline.ImageTests.make

    def test_original_resolution_and_no_crop_never_resize(self):
        path = self.make('original.png', (603, 401))
        for ratio in (None, (4, 3), (1, 1), (21, 9)):
            with patch.object(Image.Image, 'resize', side_effect=AssertionError('Unexpected resize')):
                result = process_image(path, ProcessingOptions(ratio))
            self.assertFalse(result.error, result.error)
            self.assertEqual(result.size, result.cropped_size)
            if ratio is None:
                self.assertEqual(result.size, (603, 401))

    def test_crop_before_one_lanczos_resize(self):
        path = self.make('landscape.png', (1600, 900))
        original_resize = Image.Image.resize
        calls = []

        def spy(image, size, resample, **kwargs):
            calls.append((image.size, size, resample, kwargs))
            return original_resize(image, size, resample, **kwargs)

        with patch.object(Image.Image, 'resize', new=spy):
            result = process_image(path, ProcessingOptions((4, 3), PRESET_BY_KEY['edge_1024']))
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.cropped_size, (1200, 900))
        self.assertEqual(result.size, (1024, 768))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ((1200, 900), (1024, 768), Image.Resampling.LANCZOS))
        self.assertIsNone(calls[0][3]['reducing_gap'])

    def test_upscaling_checked_against_crop_not_source(self):
        path = self.make('wide.png', (1800, 600))
        options = ProcessingOptions((1, 1), PRESET_BY_KEY['edge_1024'])
        result = process_image(path, options)
        self.assertFalse(result.error)
        self.assertEqual(result.size, (600, 600))
        self.assertTrue(result.upscaling_blocked)
        result = process_image(path, ProcessingOptions((1, 1), options.output, True))
        self.assertEqual(result.size, (1024, 1024))
        self.assertFalse(result.upscaling_blocked)

    def test_exact_preset_overrides_ratio_with_portrait_and_exif(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[256], exif[257] = 600, 400
        exif[34665] = {40962: 600, 40963: 400}
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        path = self.make('portrait_exif.jpg', (600, 400), exif=exif, icc_profile=profile)
        result = process_image(path, ProcessingOptions((1, 1), PRESET_BY_KEY['exact_1200_800'], True))
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.original_size, (400, 600))
        self.assertEqual(result.cropped_size, (400, 600))
        self.assertEqual(result.size, (800, 1200))
        with Image.open(result.output) as exported:
            self.assertEqual(exported.info['icc_profile'], profile)
            self.assertNotIn(274, exported.getexif())
            self.assertEqual(exported.getexif()[256], 800)
            self.assertEqual(exported.getexif()[257], 1200)
            self.assertEqual(exported.getexif().get_ifd(34665)[40962], 800)
            self.assertEqual(exported.getexif().get_ifd(34665)[40963], 1200)

    def test_no_crop_long_edge_and_tiny_source(self):
        path = self.make('original.png', (713, 419))
        result = process_image(path, ProcessingOptions(None, PRESET_BY_KEY['edge_1024'], True))
        self.assertEqual(result.cropped_size, (713, 419))
        self.assertEqual(result.size, (1024, 602))
        tiny = process_image(self.make('tiny.png', (1, 2)), ProcessingOptions(None))
        self.assertFalse(tiny.error)
        self.assertEqual(tiny.size, (1, 2))

    def test_approximate_exact_preset_small_source(self):
        path = self.make('small.png', (800, 600))
        preset = PRESET_BY_KEY['exact_2048_1365']
        result = process_image(path, ProcessingOptions(output=preset))
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.size, (800, 533))
        self.assertTrue(result.upscaling_blocked)
        result = process_image(path, ProcessingOptions(output=preset, allow_upscaling=True))
        self.assertFalse(result.error, result.error)
        self.assertEqual(result.size, (2048, 1365))

    def test_palette_transparency_uses_filtered_rgb(self):
        image = Image.new('P', (1600, 1200))
        image.putpalette([255, 0, 0, 0, 0, 255] + [0]*762)
        image.paste(1, (800, 0, 1600, 1200))
        path = self.root / 'palette.png'
        image.save(path, transparency=0)
        result = process_image(path, ProcessingOptions((4, 3), PRESET_BY_KEY['edge_1024']))
        self.assertFalse(result.error, result.error)
        with Image.open(result.output) as output:
            self.assertEqual(output.mode, 'RGB')
            self.assertEqual(output.getpixel((100, 100)), (255, 255, 255))
            self.assertGreater(output.getpixel((512, 100))[0], 0, 'LANCZOS edge should be filtered')


class SettingsGuiTests(unittest.TestCase):
    setUp = baseline.ImageTests.setUp
    tearDown = baseline.ImageTests.tearDown
    make = baseline.ImageTests.make
    wait_idle = baseline.GuiTests.wait_idle
    setUpClass = classmethod(baseline.GuiTests.setUpClass.__func__)

    def select_output(self, window, key):
        for index in range(window.output_size.count()):
            preset = window.output_size.itemData(index)
            if preset is not None and preset.key == key:
                window.output_size.setCurrentIndex(index)
                return
        self.fail(f'Missing preset: {key}')

    def test_settings_sync_and_worker_snapshot(self):
        window = MainWindow()
        window.show()
        self.addCleanup(window.close)
        self.assertEqual(window.aspect.currentText(), '4:3')
        self.assertEqual(window.output_size.currentText(), 'Original Resolution')
        self.assertFalse(window.upscaling.isChecked())
        self.select_output(window, 'exact_3000_2000')
        self.assertEqual(window.aspect.currentText(), '3:2')
        self.assertFalse(window.aspect.isEnabled())
        self.select_output(window, 'exact_4000_3000')
        self.assertEqual(window.aspect.currentText(), '4:3')
        self.select_output(window, 'exact_3840_2160')
        self.assertEqual(window.aspect.currentText(), '16:9')
        self.select_output(window, 'exact_2048_1365')
        self.assertIn('2048:1365', window.aspect.currentText())
        self.select_output(window, 'edge_1024')
        self.assertTrue(window.aspect.isEnabled())
        window.aspect.setCurrentText('16:9')
        window.upscaling.setChecked(True)
        path = self.make('image.png', (600, 400))
        window.add_paths([path])
        self.wait_idle(window)
        window.process.click()
        self.assertFalse(window.aspect.isEnabled())
        self.assertFalse(window.output_size.isEnabled())
        self.assertFalse(window.upscaling.isEnabled())
        self.wait_idle(window)
        self.assertEqual(window.processed, 1)
        with Image.open(path.parent / '4x3_cropped' / 'image.jpg') as image:
            self.assertEqual(image.size, (1024, 576))
        self.assertIn('resized', window.table.item(0, 1).text())
        self.assertIn('16:9', window.summary.text())
        self.assertTrue(window.aspect.isEnabled())
        window.grab().save('test-results/gui-v2-tested.png')
        for index in range(window.output_size.count()):
            if window.output_size.itemData(index) is None:
                self.assertFalse(window.output_size.model().item(index).isEnabled())
