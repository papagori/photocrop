# PhotoCropV2

A lightweight Python desktop app for batch cropping and resizing images with selectable aspect ratios, standard output sizes, drag-and-drop support, and high-quality JPEG export.

Built with **PySide6** and **Pillow**, with Windows as the primary platform. Processing runs in a background thread so the interface remains responsive.

## Features

- Drag and drop multiple files or folders, or click to open a file/folder picker.
- Optional recursive folder scanning, duplicate detection, and per-image error reporting.
- EXIF-aware orientation and centered cropping: portrait images automatically use the inverse ratio.
- Aspect ratios: Original / No Crop, 1:1, 4:3, 3:2, 5:4, 16:9, 16:10, and 21:9.
- Original Resolution, long-edge sizes, and exact photo/video resolution presets.
- No upscaling by default; optional **Allow Upscaling**.
- A single high-quality LANCZOS resize after cropping, when requested.
- JPEG export with `quality=100`, `subsampling=0`, and `optimize=True`.
- ICC profiles and relevant EXIF metadata preserved where supported; EXIF orientation removed after applying it.
- Unicode paths supported, including accents, Japanese characters, and spaces.
- Originals are never overwritten; output filename collisions receive numbered suffixes.

## Requirements

- Python **3.10 or newer**; Windows x64 recommended.
- **Pillow** and **PySide6**, specified in [requirements.txt](requirements.txt).
- **PyInstaller** is needed only to build an executable; see [requirements-dev.txt](requirements-dev.txt).

No database, account, or network connection is needed to process images. Dependency installation requires access to the Python package index.

## Installation

In PowerShell:

```powershell
git clone https://github.com/papagori/photocrop.git
cd photocrop
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python.exe main.py
```

## Basic usage

1. Drop images or a folder into the central area, or click it and choose **Add files…** or **Add folder…**.
2. Enable **Include subfolders** before adding a folder if recursive scanning is needed.
3. Choose **Aspect Ratio** and **Output Size**. The defaults are **4:3**, **Original Resolution**, and upscaling disabled.
4. Click **Process**. Review final dimensions, output paths, and any errors in the file list and log.
5. Use **Clear** to empty the list. This does not delete images or reset your selected settings.

Outputs are saved in a **`4x3_cropped`** folder beside each source image. This historical folder name is used for all selected ratios. Files from different source directories each receive their own output folder. Existing output names become `name_2.jpg`, `name_3.jpg`, and so on. Processing the same batch again creates new copies.

Generated output folders are excluded from folder scanning. Unsupported extensions and duplicates are skipped. A corrupt image does not stop the batch. Wait for the current operation to finish before closing the application.

## Crop and output settings

EXIF orientation is applied before deciding whether an image is landscape or portrait. Square images are treated as landscape. For example, selecting 4:3 produces 4:3 for landscape and 3:4 for portrait; selecting 16:9 produces 16:9 or 9:16.

**Original / No Crop** keeps the original aspect ratio after orientation, subject to integer rounding if resizing. **Original Resolution** performs no resize: only the chosen crop is applied.

| Output group | Available sizes |
| --- | --- |
| Original Resolution | All remaining pixels after cropping |
| Long Edge | 1K / 1024, 2K / 2048, 3K / 3072, 4K / 4096, 5K / 5120, 6K / 6144, 8K / 8192 px |
| Photo Presets | 1200 × 800, 1500 × 1000, 2048 × 1365, 2400 × 1600, 3000 × 2000, 4000 × 3000, 4500 × 3000, 5000 × 3333, 6000 × 4000, 6000 × 4500 px |
| Video / Screen Presets | 1920 × 1080, 2560 × 1440, 3840 × 2160, 7680 × 4320 px |

**Long Edge** respects the independently selected aspect ratio. The longest side has the stated pixel length, while the shorter side is rounded to the nearest pixel. For example, 4096 px produces 4096 × 3072 at 4:3 or 4096 × 2304 at 16:9, with dimensions reversed for portrait. The 4096 px long-edge preset is distinct from the 3840 × 2160 screen preset.

**Exact presets** automatically select and lock their corresponding aspect ratio. For example, 3000 × 2000 selects 3:2, and 4000 × 3000 selects 4:3. Dimensions are reversed for portrait images. Switch back to Original Resolution or Long Edge to choose an aspect ratio freely.

2048 × 1365 and 5000 × 3333 are only approximately 3:2. Their exact ratios appear temporarily in the Aspect Ratio menu and are used for the announced output dimensions. Leaving these presets returns the menu to 3:2.

**Allow Upscaling** is off by default. When the requested dimensions exceed the image size **after cropping**, resizing is skipped and the full cropped resolution is retained. The list reports **upscaling avoided**. This rule takes precedence over exact preset dimensions. Enable the option to permit enlargement.

## Image quality and limitations

The pipeline is: read → apply EXIF orientation → determine orientation → centered crop → optional single resize → JPEG export. Images are not stretched or padded with borders.

Standard ratios use the largest exact integer-ratio rectangle. For example, 6000 × 4000 becomes **5332 × 3999** at 4:3 with Original Resolution. Centered margins may differ by one pixel. Already-correct dimensions are not cropped again.

For the two approximate-3:2 presets, the crop is rounded to integer pixels to avoid excessive pixel loss. During resizing, a fractional edge correction matches the exact output ratio. If upscaling is blocked, the retained integer crop can differ from the requested ratio by a one-pixel rounding. Long-edge rounding can also require an edge correction during resampling.

Resizing uses `Image.Resampling.LANCZOS` in a single call from the cropped image, with `reducing_gap=None`. Palette and bilevel images are converted before filtering. Transparency is composited onto white before JPEG export.

JPEG is **lossy even at quality 100**. Images are re-encoded even when cropping and resizing are unnecessary. Outputs can be large. Compatible ICC profiles are retained; RGB, grayscale, and CMYK keep their color spaces, while LAB is color-managed into sRGB. Relevant EXIF fields are preserved where Pillow supports them, and existing dimension fields are updated after resizing. Embedded previews and format-specific metadata are not guaranteed to survive.

Supported inputs: **JPG/JPEG, PNG, TIFF/TIF, and WEBP**. Animated images, multipage TIFFs, and 16/32-bit images are reported as errors to avoid silently dropping pages or making an implicit tone-mapping choice. Images too small for an exact standard-ratio crop are also reported; No Crop accepts very small images.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers crop geometry, all ratio and output presets, EXIF orientation, metadata, image formats, transparency, Unicode paths, collisions, corruption, no-upscaling behavior, single-pass resizing, Qt drag-and-drop events, menu synchronization, and background batches. See [TEST_REPORT.md](TEST_REPORT.md).

## Build a standalone Windows executable

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name PhotoCropV2 main.py
```

The result is **`dist\PhotoCropV2.exe`**. Build on Windows to produce a Windows executable. Python is not required on the machine running that executable. The executable is unsigned and can take a few seconds to start while extracting its components.

Alternatively, run `powershell -ExecutionPolicy Bypass -File .\build.ps1`. This prepares dependencies, runs the tests, builds the executable, and verifies three batches in the compiled application.

To run the compiled verification explicitly:

```powershell
Start-Process -FilePath .\dist\PhotoCropV2.exe -ArgumentList '--self-test', 'test-results\compiled-v2.json' -WindowStyle Hidden -Wait
Get-Content test-results\compiled-v2.json
```

This opt-in mode uses temporary synthetic images and the Qt offscreen plugin. It writes a JSON report (`passed: true`, `frozen: true` on success) and a PNG capture. Normal launching does not run these checks. Executables, build outputs, backups, virtual environments, and generated test files are not tracked in this repository.

## Project structure

- `main.py`: application entry point and optional compiled verification.
- `cropper/gui.py`: Qt interface, settings synchronization, and worker thread.
- `cropper/settings.py`: shared preset catalog and immutable processing options.
- `cropper/geometry.py`: crop and output-size calculations.
- `cropper/discovery.py`: input discovery, filtering, and deduplication.
- `cropper/processing.py`: image processing pipeline and per-file error handling.
- `cropper/export.py`: color conversion, metadata, and exclusive JPEG output creation.
- `cropper/smoke.py`: standalone build verification.
- `tests/`: automated tests using Python's standard `unittest` module.

## License

PhotoCropV2 is licensed under the **GNU General Public License, version 3.0 only** (`GPL-3.0-only`). The complete official license text is provided in [LICENSE](LICENSE).

Third-party dependencies are distributed under their respective licenses.
