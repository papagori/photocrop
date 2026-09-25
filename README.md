# PhotoCrop

PhotoCrop is a lightweight open-source Windows utility for fast batch cropping and resizing. Choose a ratio, select an output size, preview the crop, and process your images without opening a full photo editor.

## Download for Windows

**Recommended installer:** `PhotoCrop_Setup.exe`

- **Release:** [PhotoCrop 2.2.2](https://github.com/papagori/photocrop/releases/tag/v2.2.2)
- **Direct installer:** [Download PhotoCrop_Setup.exe](https://github.com/papagori/photocrop/releases/download/v2.2.2/PhotoCrop_Setup.exe)
- **SHA-256:** `F90DE9AC34909E9BE55DD1053D2E888A340FEC89B60A37A0B2D86F8CB6C740E7`

The installer is the recommended way to use PhotoCrop on Windows. It is available in **English**, **Français**, and **日本語**.

## For users

The Windows installer includes everything required to run PhotoCrop. You do **not** need to install Python, PySide6, Pillow, the Microsoft Visual C++ Runtime, PyInstaller, or Inno Setup.

### Features

- Drag and drop image files or folders, with optional recursive folder scanning.
- Process many images in one batch without modifying the originals.
- Choose from **Original, 1:1, 3:2, 4:3, 5:4, 16:9, and 2:1** ratios.
- Use output presets that update dynamically for the selected ratio and reverse automatically for portrait images.
- Keep the largest possible crop with **Maximum Resolution**, or choose a standard output size.
- Preview the crop before processing, with an overlay showing the areas that will be removed.
- Export to **JPEG, PNG, or TGA**; PNG and TGA preserve source alpha transparency.
- Apply EXIF orientation before crop calculations.
- Preserve compatible ICC profiles and relevant metadata where supported.
- Resize in a single high-quality **LANCZOS** pass.
- Avoid upscaling by default, with an option to allow it when needed.
- Save exports beside each source in a `PhotoCrop_Export` folder.
- Optionally open the first output folder automatically after a successful batch.
- Switch between **Dark, Light, and Classic** themes; Classic uses its own retro low-color pixel icons.
- Use the application in **English**, **Français**, or **日本語**.

### Usage

1. Drag image files or a folder into PhotoCrop.
2. Select an aspect ratio.
3. Keep **Maximum Resolution** or select one of the sizes offered for that ratio.
4. Select JPEG, PNG, or TGA output.
5. Check the crop preview and overlay.
6. Click **Process**.
7. Find the exported files in `PhotoCrop_Export` beside the source images.

On first launch, PhotoCrop starts with **4:3** and **Maximum Resolution** selected. Choosing **Original** disables cropping and offers **Original Resolution** plus 2000, 3000, 4000, 5000, 6000, and 8000 px long-edge choices.

For cropped ratios, **Maximum Resolution** keeps the largest centered crop without resizing. Standard presets depend on the selected ratio; for example, 1:1 includes 1024, 2048, 4096, and 8192 px square outputs. If a requested size exceeds the available cropped image, PhotoCrop keeps the maximum available resolution unless **Allow Upscaling** is enabled.

Existing filenames receive `_2`, `_3`, and subsequent suffixes. Current and legacy generated output folders are excluded from input scanning. The optional automatic folder opening occurs once, after a successful batch.

### Supported images

PhotoCrop accepts JPG/JPEG, PNG, TIFF/TIF, and WEBP source images. It exports JPEG, PNG, and TGA. Animated images and multipage TIFF files are reported as errors.

JPEG export uses quality 100, 4:4:4 sampling, and optimization; transparency is composited onto white. PNG is lossless, and PNG/TGA retain source alpha. Compatible ICC profiles, EXIF data, and DPI metadata are retained where the selected output format supports them.

## For developers / Running from source

Python **3.10 or newer** is required only when running or developing PhotoCrop from source.

```powershell
git clone https://github.com/papagori/photocrop.git
cd photocrop
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Tests and validation

Run the automated suite with:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The current PhotoCrop 2.2.2 release validation includes:

- **34 automated tests**.
- Frozen `PhotoCropV2.exe` validation through its packaged self-test.
- Installer install/run/uninstall validation in an isolated location.
- Windows Sandbox validation of the public Windows distribution.
- JPEG, PNG, and TGA output, including PNG/TGA alpha handling.
- The three application and installer languages: **English, Français, 日本語**.
- The three themes: **Dark, Light, Classic**.
- Crop geometry, dynamic presets, portrait inversion, preview dimensions, EXIF orientation, ICC/metadata handling, no-upscaling behavior, single-pass LANCZOS resizing, drag and drop, background batches, and output-folder behavior.

See [TEST_REPORT.md](TEST_REPORT.md) for the release validation summary.

### Windows executable and installer builds

Install the development dependencies and run the complete build:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The build script generates the shared icon, runs the 34 tests, builds the one-file `dist\PhotoCropV2.exe` binary with PyInstaller, and runs its frozen self-test. If Inno Setup 6 is installed, the script also builds `dist\PhotoCrop_Setup.exe` from `installer\PhotoCropV2.iss`.

To build only the executable with PyInstaller:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean PhotoCropV2.spec
```

To compile the installer directly with Inno Setup 6 after building the executable:

```powershell
ISCC.exe /DAppVersion=2.2.2 installer\PhotoCropV2.iss
```

The installer can be validated with a silent isolated install, frozen application self-test, and uninstall:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\test_installer.ps1
```

The release version is defined in `cropper/version.py` and reused by the application, Windows executable metadata, and installer build.

### Project structure

- `main.py`: application entry point and standalone self-test switch.
- `cropper/gui.py`: interface, dynamic menus, preview, and worker thread.
- `cropper/settings.py`: ratio-specific output catalog and processing options.
- `cropper/geometry.py`: crop and output dimension calculations.
- `cropper/processing.py`: EXIF orientation, cropping, and single-pass resize pipeline.
- `cropper/export.py`: JPEG/PNG/TGA color, alpha, metadata, and output handling.
- `cropper/i18n.py`: English, Français, and 日本語 application text catalogs.
- `cropper/discovery.py`: input discovery and filtering.
- `cropper/themes.py`: Dark, Light, and Classic theme definitions.
- `cropper/classic_icons.py`: retro low-color pixel icons used by the Classic theme.
- `cropper/smoke.py`: frozen executable validation.
- `cropper/version.py`: single application version source.
- `assets/photocrop.ico`: shared Windows application and installer icon.
- `PhotoCropV2.spec`: PyInstaller configuration for the current technical binary name.
- `installer/PhotoCropV2.iss`: Inno Setup installer configuration.
- `tools/test_installer.ps1`: isolated install/run/uninstall distribution test.
- `tests/`: automated test suite.

## License

PhotoCrop is licensed under the **GNU General Public License v3.0 only** (`GPL-3.0-only`). See [LICENSE](LICENSE) for the full license text.
