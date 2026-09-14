"""Create deterministic UI review captures for every PhotoCrop theme."""
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtWidgets import QApplication

from cropper.gui import MainWindow


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'test-results'


def wait_idle(app, window):
    deadline = time.monotonic() + 20
    while window.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    if window.busy:
        raise TimeoutError('UI capture worker timed out')


def make_images(directory):
    paths = []
    for index, size in enumerate(((900, 600), (600, 900), (800, 800))):
        image = Image.new('RGB', size, ('#326da8', '#9a5b45', '#477a59')[index])
        draw = ImageDraw.Draw(image)
        draw.rectangle((size[0] // 4, size[1] // 4,
                        size[0] * 3 // 4, size[1] * 3 // 4), outline='white', width=8)
        path = directory / f'sample-{index + 1}.png'
        image.save(path)
        paths.append(path)
    return paths


def main():
    OUTPUT.mkdir(exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    variants = (('dark', 'en'), ('light', 'fr'), ('classic', 'ja'))
    with tempfile.TemporaryDirectory(prefix='photocrop-ui-captures-') as temporary:
        paths = make_images(Path(temporary))
        for theme, language in variants:
            window = MainWindow(language=language, theme=theme)
            window.open_when_finished.blockSignals(True)
            window.open_when_finished.setChecked(True)
            window.open_when_finished.blockSignals(False)
            window.show()
            app.processEvents()
            window.grab().save(str(OUTPUT / f'ui-{theme}-{language}-empty.png'))
            window.add_paths(paths)
            wait_idle(app, window)
            window.table.selectRow(1)
            app.processEvents()
            window.grab().save(str(OUTPUT / f'ui-{theme}-{language}-preview.png'))
            if theme == 'light':
                window.output_size.setFocus()
                app.processEvents()
                window.grab().save(str(OUTPUT / 'ui-light-fr-dropdown-focus.png'))
                window.output_size.showPopup()
                app.processEvents()
                window.output_size.view().grab().save(
                    str(OUTPUT / 'ui-light-fr-dropdown-menu.png'))
                window.output_size.hidePopup()
            window.close()
            app.processEvents()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
