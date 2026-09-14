# PhotoCropV2

A lightweight bilingual desktop app for batch cropping and resizing images with selectable aspect ratios, live crop preview, standard output sizes, drag-and-drop support, and JPEG, PNG, or TGA export.

PhotoCropV2 uses PySide6 and Pillow. Batch processing runs in a background thread, and the original files are never modified.

## Features

- Drag and drop files or folders, with optional recursive scanning and batch processing.
- EXIF-aware orientation and centered cropping.
- A strict two-step workflow: choose the aspect ratio, then choose a compatible output size.
- Ratios: Original, 1:1, 3:2, 4:3, 5:4, 16:9, and 2:1.
- Maximum Resolution keeps the largest possible crop and never resizes.
- Standard dimensions are filtered by ratio and reversed automatically for portrait images.
- Original keeps the source ratio and offers Original Resolution or 2000–8000 px long-edge outputs.
- No upscaling by default, with an optional **Allow Upscaling** setting.
- One direct LANCZOS resize after cropping when a resize is requested.
- A live preview of the selected image showing Source, Crop, and Output before processing.
- A dark overlay showing exactly which areas the crop will remove.
- JPEG uses quality 100, 4:4:4 sampling, and optimization. PNG is lossless, and PNG/TGA retain source alpha.
- ICC profiles and relevant EXIF metadata are retained where supported.
- English, French, and Japanese UI with a remembered in-app language selector.
- Dark, Light, and Classic themes, remembered between sessions.
- Compact themed toggles, restrained icons, and a GPL/GitHub footer.
- High-contrast dropdown fields with explicit arrow buttons and focus/open states.
- A dedicated original low-color pixel icon set used only by the Classic theme.
- Optional opening of the first output folder once after a successful batch.

## Requirements and installation

Python 3.10 or newer is required. Windows x64 is the primary platform.

```powershell
git clone https://github.com/papagori/photocrop.git
cd photocrop
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the application with:

```powershell
.\.venv\Scripts\python.exe main.py
```

## Output presets

The Output Size menu is rebuilt whenever the aspect ratio changes, so an incompatible size cannot be selected. Each cropped ratio begins with **Maximum Resolution — Keep Maximum Pixels**, followed by standard resolutions tailored to that ratio. The 1:1 catalog provides the texture-friendly 1024, 2048, 4096, and 8192 square sizes. Portrait images display and export non-square presets with their dimensions reversed.

Selecting **Original** never crops. It offers Original Resolution and 2000, 3000, 4000, 5000, 6000, or 8000 px long-edge choices.

If a requested size is larger than the available cropped image, PhotoCropV2 retains the maximum available resolution. Enable **Allow Upscaling** to permit enlargement. Every requested resize uses one direct high-quality LANCZOS pass after cropping.

### Typical workflow

1. Drop images or a folder into PhotoCropV2.
2. Select an aspect ratio.
3. Keep **Maximum Resolution** or select a compatible output size.
4. Check the crop preview.
5. Click **Process**.
6. Retrieve the exported JPEG, PNG, or TGA files.

## Processing details

The default is 4:3 at Maximum Resolution. Portrait sources automatically use the inverse ratio, such as 3:4. For a 6000 × 4000 source, Maximum Resolution produces a 5333 × 4000 crop at 4:3 or a 6000 × 3375 crop at 16:9.

EXIF orientation is applied before PhotoCropV2 determines whether an image is landscape or portrait. Compatible ICC profiles and relevant EXIF metadata are retained when Pillow supports them.

Outputs are saved in a `PhotoCrop_Export` folder beside each source image, for every ratio, size, format, and orientation. Existing names receive `_2`, `_3`, and subsequent suffixes. Current and legacy generated output folders are excluded from input scanning.

Supported inputs are JPG/JPEG, PNG, TIFF/TIF, and WEBP. Animated images and multipage TIFF files are reported as errors. Transparency is composited onto white for JPEG output and retained for PNG/TGA output. JPEG remains the default format.

## Tests

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover crop geometry, all square texture presets, portrait inversion, preview dimensions, EXIF orientation, metadata, JPEG/PNG/TGA and alpha handling, no-upscaling behavior, direct single-pass resizing, both UI languages, output-folder timing, drag and drop, background batches, and distribution configuration.

## Windows build

Run the existing build script:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The script checks or installs the development dependencies, generates the shared application icon, runs the tests, builds `dist\PhotoCropV2.exe` from `PhotoCropV2.spec`, and launches its frozen self-test. When Inno Setup 6 is installed, it also builds `dist\PhotoCrop_Setup.exe` from `installer\PhotoCropV2.iss`.

The release version is defined once in `cropper/version.py` and reused by the application, the Windows executable metadata, and the installer build. The optional installer distribution test performs a silent isolated install, runs the installed executable's frozen self-test, and uninstalls it:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1
```

`PhotoCropV2.exe` is a PyInstaller one-file application. It contains Python, PySide6/Qt, Pillow, the required Qt plugins, the Visual C++ runtime DLLs used by the packaged modules, and the application icon. End users need only `PhotoCrop_Setup.exe`; they do not need Python, Pillow, PySide6, PyInstaller, Inno Setup, Visual Studio, or a separate Microsoft Visual C++ Redistributable installation.

Build products, installer outputs, test artifacts, caches, and the virtual environment are ignored by Git.

## Project structure

- `main.py`: application entry point and standalone self-test switch.
- `cropper/gui.py`: interface, dynamic menus, preview, and worker thread.
- `cropper/settings.py`: ratio-specific output catalog and processing options.
- `cropper/geometry.py`: crop and output dimension calculations.
- `cropper/processing.py`: image processing pipeline.
- `cropper/export.py`: JPEG/PNG/TGA color, alpha, metadata, and output handling.
- `cropper/i18n.py`: English/French application text catalog.
- `cropper/discovery.py`: input discovery and filtering.
- `cropper/smoke.py`: packaged executable verification.
- `cropper/version.py`: single application version source.
- `assets/photocrop.ico`: shared Windows application and installer icon.
- `PhotoCropV2.spec`: versioned PyInstaller configuration.
- `installer/PhotoCropV2.iss`: Inno Setup installer configuration.
- `tools/test_installer.ps1`: isolated install/run/uninstall distribution test.
- `tests/`: automated test suite.

## License

PhotoCropV2 is licensed under the **GNU General Public License v3.0 only** (`GPL-3.0-only`). See [LICENSE](LICENSE) for the full license text.
