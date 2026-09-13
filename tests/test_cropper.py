import hashlib
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, JpegImagePlugin
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from cropper.discovery import discover
from cropper.processing import crop_box, process_image
from cropper.gui import MainWindow


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='crop-tests-')
        self.root = Path(self.temp.name) / 'Été à 東京'
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def make(self, name, size=(60, 40), mode='RGB', **options):
        path = self.root / name
        Image.new(mode, size).save(path, **options)
        return path

    def test_required_dimensions(self):
        for size, expected in [((6000, 4000), (5333, 4000)), ((4000, 6000), (4000, 5333)),
                               ((400, 300), (400, 300)), ((300, 400), (300, 400)),
                               ((400, 400), (400, 300))]:
            with self.subTest(size=size):
                path = self.make(f'{size[0]}_{size[1]}.jpg', size)
                digest = hashlib.sha256(path.read_bytes()).digest()
                result = process_image(path)
                self.assertEqual(result.error, '')
                self.assertEqual(result.size, expected)
                with Image.open(result.output) as output:
                    self.assertEqual(output.size, expected)
                    self.assertEqual(JpegImagePlugin.get_sampling(output), 0)
                    self.assertTrue(all(v == 1 for table in output.quantization.values() for v in table))
                self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), digest)

    def test_exact_maximal_centered_no_resampling(self):
        for width in range(4, 80):
            for height in range(4, 80):
                x, y, right, bottom = crop_box(width, height)
                w, h = right-x, bottom-y
                a, b = (4, 3) if width >= height else (3, 4)
                self.assertTrue(w == width or h == height)
                ratio_error = min(abs(w * b / a - h), abs(h * a / b - w))
                self.assertLessEqual(ratio_error, 0.5)
                self.assertLessEqual(abs(x-(width-right)), 1)
                self.assertLessEqual(abs(y-(height-bottom)), 1)

    def test_exif_orientations_and_metadata(self):
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        for orientation in range(1, 9):
            image = Image.new('RGB', (80, 60), 'red')
            image.paste('blue', (0, 0, 40, 30))
            exif = Image.Exif()
            exif[274], exif[315], exif[306] = orientation, 'Test Photographer', '2026:09:09 12:00:00'
            path = self.root / f'exif_{orientation}.jpg'
            image.save(path, exif=exif, icc_profile=profile, quality=100, subsampling=0)
            with Image.open(path) as source:
                expected = ImageOps.exif_transpose(source)
                result = process_image(path)
                self.assertEqual(result.error, '')
                with Image.open(result.output) as output:
                    self.assertEqual(output.size, expected.size)
                    self.assertNotIn(274, output.getexif())
                    self.assertEqual(output.getexif()[315], 'Test Photographer')
                    self.assertEqual(output.info['icc_profile'], profile)
                    for point in [(10, 10), (output.width-10, output.height-10)]:
                        self.assertLess(max(abs(a-b) for a, b in zip(output.getpixel(point), expected.getpixel(point))), 5)

    def test_formats_transparency_and_collisions(self):
        for extension in ('png', 'tiff', 'tif', 'webp', 'jpeg', 'JPG'):
            path = self.make('été 日本.' + extension)
            result = process_image(path)
            self.assertFalse(result.error, result.error)
            self.assertTrue(result.output.is_file())
        alpha = self.make('transparent.png', (40, 30), 'RGBA')
        result = process_image(alpha)
        with Image.open(result.output) as output:
            self.assertEqual(output.mode, 'RGB')
            self.assertEqual(output.getpixel((10, 10)), (255, 255, 255))
        second = process_image(alpha)
        self.assertEqual(second.output.name, 'transparent_2.jpg')

    def test_discovery(self):
        path = self.make('photo.jpg')
        (self.root / 'note.txt').write_text('ignored')
        nested = self.root / 'sous dossier'
        nested.mkdir()
        Image.new('RGB', (40, 30)).save(nested / '日本.png')
        process_image(path)
        flat = discover([self.root])
        self.assertEqual(flat.files, [path.resolve()])
        recursive = discover([self.root, path], recursive=True)
        self.assertEqual(len(recursive.files), 2)
        self.assertFalse(any('4x3_cropped' in str(p) for p in recursive.files))
        self.assertEqual(discover([self.root], existing=recursive.files).files, [])

    def test_corrupt_and_small_images(self):
        corrupt = self.root / 'broken.jpg'
        corrupt.write_bytes(b'not an image')
        self.assertTrue(process_image(corrupt).error)
        tiny = self.make('tiny.png', (2, 2))
        self.assertFalse(process_image(tiny).error)
        good = process_image(self.make('good.png'))
        self.assertFalse(good.error)

    def test_multiple_source_folders(self):
        first = self.make('same.png', (40, 30))
        other = self.root / 'autre 東京'
        other.mkdir()
        second = other / 'same.png'
        Image.new('RGB', (40, 30)).save(second)
        for path in discover([first, second]).files:
            result = process_image(path)
            self.assertFalse(result.error)
            self.assertEqual(result.output.parent, path.parent / '4x3_cropped')
            self.assertEqual(result.output.name, 'same.jpg')

    def test_multipage_and_high_bit_depth_report_errors(self):
        path = self.root / 'pages.tif'
        image = Image.new('RGB', (40, 30))
        image.save(path, save_all=True, append_images=[image])
        self.assertIn('Multi-page', process_image(path).error)
        deep = self.make('deep.tif', (40, 30), 'I;16')
        self.assertIn('16/32-bit', process_image(deep).error)


class GuiTests(unittest.TestCase):
    setUp = ImageTests.setUp
    tearDown = ImageTests.tearDown
    make = ImageTests.make
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_gui_drop_worker_and_batch(self):
        window = MainWindow()
        window.show()
        first = self.make('photo.jpg')
        second = self.make('vertical.png', (30, 45))
        broken = self.root / 'corrompu.jpg'
        broken.write_bytes(b'broken')
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in [first, second, broken]])
        enter = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime,
                               Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(window.drop, enter)
        self.assertTrue(enter.isAccepted())
        drop = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime,
                         Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(window.drop, drop)
        self.wait_idle(window)
        self.assertEqual(len(window.paths), 3)
        window.process.click()
        self.assertFalse(window.clear.isEnabled())
        self.wait_idle(window)
        self.assertEqual(window.processed, 2)
        self.assertEqual(window.errors, 1)
        self.assertEqual(window.progress.value(), 3)
        self.assertIn('Finished: 2 images processed', window.status.text())
        folder = Path('test-results')
        folder.mkdir(exist_ok=True)
        window.grab().save(str(folder / 'gui-tested.png'))
        window.clear.click()
        self.assertEqual(window.table.rowCount(), 0)
        self.assertEqual(window.status.text(), 'Ready')
        mime.setUrls([QUrl.fromLocalFile(str(self.root))])
        self.app.sendEvent(window.drop, QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction,
                           mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.app.sendEvent(window.drop, QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction,
                           mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.wait_idle(window)
        self.assertEqual(len(window.paths), 3)
        window.close()

    def wait_idle(self, window):
        deadline = time.monotonic() + 30
        while window.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertFalse(window.busy, 'Worker did not finish')


if __name__ == '__main__':
    unittest.main()
