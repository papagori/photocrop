# PhotoCropV2

A lightweight Python desktop app for batch cropping and resizing images with selectable aspect ratios, live crop preview, standard output sizes, drag-and-drop support, and high-quality JPEG export.

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
- ICC profiles and relevant EXIF metadata are retained where supported.
- High-quality JPEG export to a dedicated folder beside each source folder.

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

The Output Size menu is rebuilt whenever the aspect ratio changes, so an incompatible size cannot be selected. Each cropped ratio begins with **Maximum Resolution — Keep Maximum Pixels**, followed by standard resolutions tailored to that ratio. Portrait images display and export the same presets with their dimensions reversed.

Selecting **Original** never crops. It offers Original Resolution and 2000, 3000, 4000, 5000, 6000, or 8000 px long-edge choices.

If a requested size is larger than the available cropped image, PhotoCropV2 retains the maximum available resolution. Enable **Allow Upscaling** to permit enlargement. Every requested resize uses one direct high-quality LANCZOS pass after cropping.

### Typical workflow

1. Drop images or a folder into PhotoCropV2.
2. Select an aspect ratio.
3. Keep **Maximum Resolution** or select a compatible output size.
4. Check the crop preview.
5. Click **Process**.
6. Retrieve the exported JPEG files.

## Processing details

The default is 4:3 at Maximum Resolution. Portrait sources automatically use the inverse ratio, such as 3:4. For a 6000 × 4000 source, Maximum Resolution produces a 5333 × 4000 crop at 4:3 or a 6000 × 3375 crop at 16:9.

EXIF orientation is applied before PhotoCropV2 determines whether an image is landscape or portrait. Compatible ICC profiles and relevant EXIF metadata are retained when Pillow supports them.

Outputs are saved in a `4x3_cropped` folder beside each source image. This historical folder name is used for every ratio. Existing names receive `_2`, `_3`, and subsequent suffixes. Generated output folders are excluded from input scanning.

Supported inputs are JPG/JPEG, PNG, TIFF/TIF, and WEBP. Animated images, multipage TIFF files, and 16/32-bit images are reported as errors. Transparency is composited onto white for JPEG output.

## Tests

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover crop geometry, every ratio-specific menu, portrait inversion, preview dimensions, EXIF orientation, metadata, supported formats, no-upscaling behavior, direct single-pass resizing, drag and drop, and background batches.

## Windows build

Run the existing build script:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The script installs build dependencies, runs the tests, creates `dist\PhotoCropV2.exe` with PyInstaller, and launches its built-in standalone verification. Build products, test artifacts, caches, and the virtual environment are ignored by Git.

## Project structure

- `main.py`: application entry point and standalone self-test switch.
- `cropper/gui.py`: interface, dynamic menus, preview, and worker thread.
- `cropper/settings.py`: ratio-specific output catalog and processing options.
- `cropper/geometry.py`: crop and output dimension calculations.
- `cropper/processing.py`: image processing pipeline.
- `cropper/export.py`: JPEG color, metadata, and output handling.
- `cropper/discovery.py`: input discovery and filtering.
- `cropper/smoke.py`: packaged executable verification.
- `tests/`: automated test suite.

## License

PhotoCropV2 is licensed under the **GNU General Public License v3.0 only** (`GPL-3.0-only`). See [LICENSE](LICENSE) for the full license text.
