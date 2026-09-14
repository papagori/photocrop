import re
import unittest
from pathlib import Path

from PIL import Image

from cropper.resources import resource_path
from cropper.version import __version__


ROOT = Path(__file__).resolve().parent.parent


class DistributionConfigurationTests(unittest.TestCase):
    def test_version_and_icon_source(self):
        self.assertRegex(__version__, r'^\d+\.\d+\.\d+$')
        icon = resource_path('assets/photocrop.ico')
        self.assertTrue(icon.is_file())
        self.assertGreater(icon.stat().st_size, 1000)
        with Image.open(icon) as image:
            self.assertEqual(image.format, 'ICO')
            self.assertIn((256, 256), image.ico.sizes())
            self.assertIn((16, 16), image.ico.sizes())

    def test_pyinstaller_spec_embeds_runtime_resources(self):
        spec = (ROOT / 'PhotoCropV2.spec').read_text(encoding='utf-8')
        self.assertIn("datas=[('assets/photocrop.ico', 'assets')]", spec)
        self.assertIn("icon='assets/photocrop.ico'", spec)
        self.assertIn('version=version_info', spec)
        self.assertIn("name='PhotoCropV2'", spec)

    def test_inno_setup_installs_only_the_bundled_executable(self):
        script_path = ROOT / 'installer' / 'PhotoCropV2.iss'
        self.assertTrue(script_path.read_bytes().startswith(b'\xef\xbb\xbf'))
        script = script_path.read_text(encoding='utf-8-sig')
        self.assertIn('Source: "..\\dist\\{#AppExeName}"', script)
        self.assertIn('UninstallDisplayIcon={app}\\{#AppExeName}', script)
        self.assertIn('Tasks: desktopicon', script)
        self.assertIn('Name: "french"', script)
        self.assertIn('Name: "japanese"', script)
        self.assertIn('JapaneseOverrides.isl', script)
        self.assertIn("FontExists('Yu Gothic UI')", script)
        self.assertIn('japanese.DesktopShortcut=\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\u306b\u30b7\u30e7\u30fc\u30c8\u30ab\u30c3\u30c8\u3092\u4f5c\u6210\u3059\u308b', script)
        self.assertIn('ValueName: "language"', script)
        self.assertIn("if ActiveLanguage = 'french'", script)
        self.assertIn("if ActiveLanguage = 'japanese'", script)
        self.assertNotIn('file association', script.lower())
        self.assertIsNone(re.search(r'\b(python|pip|pyinstaller|iscc)\.exe\b', script, re.I))

        overrides = (ROOT / 'installer' / 'JapaneseOverrides.isl').read_text(encoding='utf-8')
        self.assertIn('DialogFontName=Yu Gothic UI', overrides)
        self.assertIn('WelcomeFontName=Yu Gothic UI', overrides)


if __name__ == '__main__':
    unittest.main()
