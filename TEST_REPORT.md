# PhotoCropV2 validation

Validated on Windows x64 with Python 3.10.6, Pillow 12.3.0, PySide6 6.11.0, PyInstaller 6.20.0, and Inno Setup 6.7.3.

## Automated validation

Run from the repository root:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All **22 tests passed**. Coverage includes crop and resize geometry, dynamic ratio-specific presets, portrait inversion, no-upscaling behavior, one-pass LANCZOS resizing, metadata and color handling, input discovery, Qt drag and drop, preview dimensions, worker batches, and Windows distribution configuration.

The image-processing behavior was not changed during the Windows UI and packaging work.

## Frozen executable

`PhotoCropV2.exe` was built from the versioned `PhotoCropV2.spec` as a one-file windowed application. Its explicit `--self-test` completed with exit code 0 and reported:

- `passed: true`
- `frozen: true`
- version `2.0.0`
- bundled application icon found
- Qt plugin directory found
- no external Python required

The three frozen processing batches produced the expected landscape and portrait outputs and continued correctly after a deliberately corrupt input.

Archive inspection confirmed that the executable contains:

- `python310.dll` and the Python standard library archive
- PySide6 and Qt runtime DLLs
- the Windows platform plugin `qwindows.dll`
- Qt image format plugins for JPEG, TIFF, WEBP, ICO, GIF, and SVG
- Pillow imaging, color-management, AVIF, and WEBP extensions
- `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, and required MSVC C++ DLLs
- `assets/photocrop.ico`

The outer executable imports only standard Windows system libraries such as KERNEL32, USER32, GDI32, ADVAPI32, and COMCTL32. A separate Microsoft Visual C++ Redistributable installation is not required.

## Installer

Inno Setup produced `dist\PhotoCrop_Setup.exe`. The installer was tested with a silent isolated installation under `test-results`, without using the development virtual environment. The installed `PhotoCropV2.exe` passed the same frozen self-test, the uninstaller was present, and silent uninstallation removed the test installation directory completely.

Inno Setup is required only on the development machine to compile the installer. It is not installed or invoked on an end-user machine.

Generated executables, installers, reports, screenshots, caches, virtual environments, and local backups remain excluded from Git.
