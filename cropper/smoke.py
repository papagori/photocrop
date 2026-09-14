"""Opt-in standalone build verification with temporary synthetic inputs."""
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

import PIL
import PySide6
from PIL import Image
from PySide6.QtCore import QLibraryInfo
from PySide6.QtWidgets import QApplication

from .gui import MainWindow
from .resources import resource_path
from .version import __version__


def run(report_path):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    frozen = bool(getattr(sys, 'frozen', False))
    report = {'passed': False, 'frozen': frozen, 'version': __version__,
              'pillow': PIL.__version__, 'pyside6': PySide6.__version__, 'batches': [],
              'runtime': {
                  'executable': Path(sys.executable).name,
                  'external_python_required': False,
                  'icon_bundled': resource_path('assets/photocrop.ico').is_file(),
                  'qt_plugins_available': Path(
                      QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)).is_dir(),
              }}
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    window = MainWindow(language='en', theme='dark')

    def wait_idle():
        deadline = time.monotonic() + 30
        while window.busy and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        if window.busy:
            raise TimeoutError('Qt worker did not complete within 30 seconds')

    def select_output(key):
        for index in range(window.output_size.count()):
            preset = window.output_size.itemData(index)
            if preset is not None and preset.key == key:
                window.output_size.setCurrentIndex(index)
                return
        raise AssertionError(f'Missing preset {key}')

    try:
        if frozen:
            assert Path(sys.executable).name.lower() == 'photocropv2.exe'
            assert report['runtime']['icon_bundled']
            assert report['runtime']['qt_plugins_available']
        with tempfile.TemporaryDirectory(prefix='photo-crop-v2-') as directory:
            root = Path(directory) / 'Été 東京'
            root.mkdir()
            Image.new('RGB', (600, 400), 'steelblue').save(root / 'landscape.jpg')
            Image.new('RGBA', (400, 600), (255, 128, 30, 128)).save(root / 'portrait.png')
            (root / 'broken.jpg').write_bytes(b'intentionally corrupt test image')
            window.show()
            for language, expected in (('en', 'Process'), ('fr', 'Traiter'), ('ja', '処理開始')):
                window.language_combo.setCurrentIndex(window.language_combo.findData(language))
                assert window.process.text() == expected
            for theme in ('dark', 'light', 'classic'):
                window.theme_combo.setCurrentIndex(window.theme_combo.findData(theme))
                assert window.theme == theme and window.styleSheet()
            report['ui'] = {'languages': ['en', 'fr', 'ja'],
                            'themes': ['dark', 'light', 'classic'],
                            'footer': window.footer_gpl.text(),
                            'github': 'https://github.com/papagori/photocrop'}
            window.language_combo.setCurrentIndex(window.language_combo.findData('en'))
            window.theme_combo.setCurrentIndex(window.theme_combo.findData('dark'))
            window.add_paths([root])
            wait_idle()
            assert len(window.paths) == 3
            window.aspect.setCurrentText('16:9')
            for batch, key, upscaling, expected in (
                (1, 'maximum', False, (600, 338)),
                (2, 'exact_1920_1080', True, (1920, 1080)),
                (3, 'exact_2400_1600', True, (2400, 1600)),
            ):
                if batch == 3:
                    window.aspect.setCurrentText('3:2')
                select_output(key)
                window.upscaling.setChecked(upscaling)
                assert window.aspect.isEnabled()
                window.process.click()
                wait_idle()
                assert (window.processed, window.errors) == (2, 1)
                suffix = '' if batch == 1 else f'_{batch}'
                for name, size in (('landscape', expected), ('portrait', expected[::-1])):
                    with Image.open(root / 'PhotoCrop_Export' / f'{name}{suffix}.jpg') as result:
                        assert result.size == size, (result.size, size)
                        assert result.format == 'JPEG'
                report['batches'].append({'preset': key, 'allow_upscaling': upscaling,
                    'landscape': expected, 'portrait': expected[::-1], 'processed': 2, 'expected_errors': 1})
            window.aspect.setCurrentText('1:1')
            select_output('exact_1024_1024')
            window.upscaling.setChecked(True)
            for output_format, extension, expected_mode in (
                ('PNG', '.png', ('RGB', 'RGBA')),
                ('TGA', '.tga', ('RGB', 'RGBA')),
            ):
                window.output_format.setCurrentText(output_format)
                window.process.click()
                wait_idle()
                assert (window.processed, window.errors) == (2, 1)
                for name, mode in zip(('landscape', 'portrait'), expected_mode):
                    with Image.open(root / 'PhotoCrop_Export' / f'{name}{extension}') as result:
                        assert result.size == (1024, 1024)
                        assert result.format == output_format
                        assert result.mode == mode
                report['batches'].append({'preset': 'exact_1024_1024',
                    'allow_upscaling': True, 'format': output_format,
                    'landscape': (1024, 1024), 'portrait': (1024, 1024),
                    'processed': 2, 'expected_errors': 1})
            window.grab().save(str(report_path.with_suffix('.png')))
            report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if window.worker is not None:
            window.worker.wait()
            app.processEvents()
        window.close()
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0 if report['passed'] else 1
