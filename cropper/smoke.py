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
from PySide6.QtWidgets import QApplication

from .gui import MainWindow


def run(report_path):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'frozen': bool(getattr(sys, 'frozen', False)),
              'pillow': PIL.__version__, 'pyside6': PySide6.__version__, 'batches': []}
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    window = MainWindow()

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
        with tempfile.TemporaryDirectory(prefix='photo-crop-v2-') as directory:
            root = Path(directory) / 'Été 東京'
            root.mkdir()
            Image.new('RGB', (600, 400), 'steelblue').save(root / 'landscape.jpg')
            Image.new('RGBA', (400, 600), (255, 128, 30, 128)).save(root / 'portrait.png')
            (root / 'broken.jpg').write_bytes(b'intentionally corrupt test image')
            window.show()
            window.add_paths([root])
            wait_idle()
            assert len(window.paths) == 3
            select_output('edge_1024')
            window.aspect.setCurrentText('16:9')
            for batch, key, upscaling, expected in (
                (1, 'edge_1024', False, (592, 333)),
                (2, 'edge_1024', True, (1024, 576)),
                (3, 'exact_1200_800', True, (1200, 800)),
            ):
                select_output(key)
                window.upscaling.setChecked(upscaling)
                if batch == 3:
                    assert window.aspect.currentText() == '3:2'
                    assert not window.aspect.isEnabled()
                window.process.click()
                wait_idle()
                assert (window.processed, window.errors) == (2, 1)
                suffix = '' if batch == 1 else f'_{batch}'
                for name, size in (('landscape', expected), ('portrait', expected[::-1])):
                    with Image.open(root / '4x3_cropped' / f'{name}{suffix}.jpg') as result:
                        assert result.size == size, (result.size, size)
                        assert result.format == 'JPEG'
                report['batches'].append({'preset': key, 'allow_upscaling': upscaling,
                    'landscape': expected, 'portrait': expected[::-1], 'processed': 2, 'expected_errors': 1})
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
