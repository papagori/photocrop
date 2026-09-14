import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image, ImageCms
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFrame

import test_cropper as baseline
from cropper.discovery import OUTPUT_DIR
from cropper.geometry import crop_box, output_size
from cropper.gui import GITHUB_URL, MainWindow
from cropper.i18n import TRANSLATIONS
from cropper.processing import process_image
from cropper.settings import (
    ASPECT_RATIOS, OUTPUT_PRESETS, PRESET_BY_KEY, ProcessingOptions, presets_for_ratio,
)
from cropper.themes import THEMES, ToggleSwitch


EXPECTED_SIZES = {
    '1:1': ((1024, 1024), (2048, 2048), (4096, 4096), (8192, 8192)),
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

    def test_all_square_texture_targets_with_and_without_upscaling(self):
        for edge in (1024, 2048, 4096, 8192):
            preset = PRESET_BY_KEY[f'exact_{edge}_{edge}']
            with self.subTest(edge=edge, upscaling=False):
                options = ProcessingOptions((1, 1), preset, False)
                self.assertEqual(output_size((768, 768), options), ((768, 768), True))
            with self.subTest(edge=edge, upscaling=True):
                options = ProcessingOptions((1, 1), preset, True)
                self.assertEqual(output_size((768, 768), options), ((edge, edge), False))

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
        preset = PRESET_BY_KEY['exact_1024_1024']
        result = process_image(path, ProcessingOptions((1, 1), preset))
        self.assertEqual(result.cropped_size, (600, 600))
        self.assertEqual(result.size, (600, 600))
        self.assertTrue(result.upscaling_blocked)
        result = process_image(path, ProcessingOptions((1, 1), preset, True))
        self.assertEqual(result.size, (1024, 1024))
        self.assertFalse(result.upscaling_blocked)

    def test_jpeg_png_and_tga_outputs_preserve_expected_pixels(self):
        path = self.make('alpha.png', (80, 60), 'RGBA')
        preset = PRESET_BY_KEY['exact_1024_1024']
        for output_format in ('JPEG', 'PNG', 'TGA'):
            with self.subTest(output_format=output_format):
                options = ProcessingOptions((1, 1), preset, False, output_format)
                result = process_image(path, options)
                self.assertFalse(result.error, result.error)
                self.assertEqual(result.cropped_size, (60, 60))
                self.assertEqual(result.size, (60, 60))
                self.assertEqual(result.output.suffix.lower(),
                                 {'JPEG': '.jpg', 'PNG': '.png', 'TGA': '.tga'}[output_format])
                with Image.open(result.output) as exported:
                    self.assertEqual(exported.format, output_format)
                    self.assertEqual(exported.mode, 'RGB' if output_format == 'JPEG' else 'RGBA')

    def test_all_ratios_and_formats_use_generic_output_folder(self):
        extensions = {'JPEG': '.jpg', 'PNG': '.png', 'TGA': '.tga'}
        for ratio_name in ('1:1', '4:3', '16:9'):
            for output_format, extension in extensions.items():
                with self.subTest(ratio=ratio_name, output_format=output_format):
                    safe_ratio = ratio_name.replace(':', 'x')
                    source = self.make(f'{safe_ratio}_{output_format.lower()}.png', (96, 72))
                    options = ProcessingOptions(
                        ASPECT_RATIOS[ratio_name], PRESET_BY_KEY['maximum'], False, output_format)
                    result = process_image(source, options)
                    self.assertFalse(result.error, result.error)
                    self.assertEqual(result.output.parent, source.parent / OUTPUT_DIR)
                    self.assertEqual(result.output.suffix.lower(), extension)
                    self.assertTrue(source.is_file())

    def test_all_formats_use_one_direct_lanczos_resize(self):
        path = self.make('small-alpha.png', (48, 48), 'RGBA')
        preset = PRESET_BY_KEY['exact_1024_1024']
        original_resize = Image.Image.resize
        for output_format in ('JPEG', 'PNG', 'TGA'):
            calls = []

            def spy(image, size, resample=None, box=None, **kwargs):
                calls.append((size, resample, box, kwargs))
                return original_resize(image, size, resample, box, **kwargs)

            with self.subTest(output_format=output_format), patch.object(Image.Image, 'resize', new=spy):
                result = process_image(
                    path, ProcessingOptions((1, 1), preset, True, output_format))
                self.assertFalse(result.error, result.error)
                self.assertEqual(result.size, (1024, 1024))
                direct = [call for call in calls if call[3].get('reducing_gap', False) is None]
                self.assertEqual(direct, [((1024, 1024), Image.Resampling.LANCZOS, None,
                                           {'reducing_gap': None})])

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
        window = MainWindow(language='en')
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
        with Image.open(path.parent / OUTPUT_DIR / 'portrait.jpg') as image:
            self.assertEqual(image.size, (1600, 2400))

    def test_language_is_applied_and_persisted(self):
        settings_path = Path(self.temp.name) / 'settings.ini'
        settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
        window = MainWindow(language='en', settings=settings)
        window.show()
        window.language_combo.setCurrentIndex(1)
        settings.sync()
        self.assertEqual(window.process.text(), 'Traiter')
        self.assertEqual(window.drop.title.text(), 'Déposez des fichiers ou un dossier ici')
        self.assertEqual(window.output_size.currentText(),
                         'Résolution maximale — Conserver le maximum de pixels')
        window.close()
        restored = MainWindow(settings=QSettings(str(settings_path), QSettings.Format.IniFormat))
        self.addCleanup(restored.close)
        self.assertEqual(restored.language, 'fr')

    def test_all_translation_catalogs_match_and_japanese_is_applied(self):
        self.assertEqual(set(TRANSLATIONS), {'en', 'fr', 'ja'})
        self.assertEqual(set(TRANSLATIONS['en']), set(TRANSLATIONS['fr']))
        self.assertEqual(set(TRANSLATIONS['en']), set(TRANSLATIONS['ja']))
        window = MainWindow(language='ja', theme='dark')
        self.addCleanup(window.close)
        self.assertEqual(window.process.text(), '処理開始')
        self.assertEqual(window.drop.title.text(), 'ここにファイルまたはフォルダーをドロップ')
        self.assertEqual(window.theme_combo.itemText(1), 'ライト')
        self.assertIn('プレビュー', window.preview.title.text())

    def test_three_themes_and_theme_persistence(self):
        settings_path = Path(self.temp.name) / 'theme-settings.ini'
        settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
        window = MainWindow(language='en', theme='dark', settings=settings)
        self.addCleanup(window.close)
        self.assertEqual(tuple(window.theme_combo.itemData(i)
                               for i in range(window.theme_combo.count())), THEMES)
        styles = {}
        for index, theme_name in enumerate(THEMES):
            window.theme_combo.setCurrentIndex(index)
            styles[theme_name] = window.styleSheet()
            self.assertEqual(window.theme, theme_name)
            self.assertEqual(window.recursive.theme_name, theme_name)
        self.assertEqual(len(set(styles.values())), 3)
        settings.sync()
        restored = MainWindow(language='en', settings=QSettings(
            str(settings_path), QSettings.Format.IniFormat))
        self.addCleanup(restored.close)
        self.assertEqual(restored.theme, 'classic')

    def test_toggles_icons_footer_and_github_link(self):
        window = MainWindow(language='en', theme='light')
        self.addCleanup(window.close)
        self.assertTrue(all(isinstance(widget, ToggleSwitch) for widget in
                            (window.recursive, window.upscaling, window.open_when_finished)))
        self.assertFalse(window.logo.pixmap().isNull())
        self.assertFalse(window.clear.icon().isNull())
        self.assertFalse(window.process.icon().isNull())
        self.assertEqual(window.footer_gpl.text(), 'GNU GPL v3.0')
        self.assertEqual(window.footer_github.text(), 'GitHub')
        with patch('cropper.gui.QDesktopServices.openUrl', return_value=True) as opener:
            window.footer_github.clicked.emit()
        opener.assert_called_once()
        self.assertEqual(opener.call_args.args[0].toString(), GITHUB_URL)

    def test_dropdown_emphasis_and_classic_only_icon_set(self):
        window = MainWindow(language='en', theme='dark')
        self.addCleanup(window.close)
        window.show()
        self.app.processEvents()
        dropdowns = (window.language_combo, window.theme_combo, window.aspect,
                     window.output_size, window.output_format)
        self.assertIn('QComboBox::drop-down', window.styleSheet())
        self.assertEqual(len({combo.height() for combo in dropdowns}), 1)
        self.assertTrue(all(not combo.itemIcon(0).isNull() for combo in dropdowns))
        modern_process = window.process.icon().pixmap(16, 16).toImage()
        modern_folder = window.drop.icon.pixmap().toImage()
        self.assertEqual(window.icon_theme, 'modern')
        window.theme_combo.setCurrentIndex(window.theme_combo.findData('classic'))
        self.assertEqual(window.icon_theme, 'classic')
        self.assertNotEqual(window.process.icon().pixmap(16, 16).toImage(), modern_process)
        self.assertNotEqual(window.drop.icon.pixmap().toImage(), modern_folder)
        self.assertTrue(all(not combo.itemIcon(0).isNull() for combo in dropdowns))
        classic_process = window.process.icon().pixmap(16, 16).toImage()
        window.theme_combo.setCurrentIndex(window.theme_combo.findData('light'))
        self.assertEqual(window.icon_theme, 'modern')
        self.assertNotEqual(window.process.icon().pixmap(16, 16).toImage(), classic_process)

    def test_key_panel_geometry_stays_stable_when_files_are_added(self):
        window = MainWindow(language='en', theme='dark')
        window.show()
        self.addCleanup(window.close)
        self.app.processEvents()
        names = ('settingsPanel', 'previewPanel')
        before = {name: window.findChild(QFrame, name).geometry() for name in names}
        status_height = window.status.height()
        summary_height = window.summary.height()
        paths = [self.make(f'layout-{index}.png', (80 + index, 60)) for index in range(4)]
        window.add_paths(paths)
        self.wait_idle(window)
        self.app.processEvents()
        after = {name: window.findChild(QFrame, name).geometry() for name in names}
        self.assertEqual(before, after)
        self.assertEqual(window.status.height(), status_height)
        self.assertEqual(window.summary.height(), summary_height)

    def test_output_folder_opens_once_only_after_successful_batch(self):
        first = self.make('first.png')
        second_dir = self.root / 'second'
        second_dir.mkdir()
        second = second_dir / 'second.png'
        Image.new('RGB', (60, 40)).save(second)
        window = MainWindow(language='en')
        window.show()
        self.addCleanup(window.close)
        window.open_when_finished.setChecked(True)
        window.add_paths([first, second])
        self.wait_idle(window)
        observations = []

        def opened(path):
            observations.append((Path(path), window.busy, window.progress.value()))
            return True

        with patch('cropper.gui.open_output_folder', side_effect=opened) as opener:
            window.process.click()
            self.wait_idle(window)
        opener.assert_called_once()
        self.assertEqual(observations, [(first.parent / OUTPUT_DIR, False, 2)])

    def test_output_folder_failure_is_ignored(self):
        from cropper.gui import open_output_folder
        with patch('cropper.gui.os.startfile', create=True, side_effect=OSError('Explorer failed')):
            self.assertFalse(open_output_folder(self.root))


if __name__ == '__main__':
    unittest.main()
