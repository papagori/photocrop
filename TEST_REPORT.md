# PhotoCropV2 validation

Validated on Windows x64 with Python 3.10.6, Pillow 12.3.0, PySide6 6.11.0, PyInstaller 6.20.0, and Inno Setup 6.7.3.

## Automated validation

Run from the repository root:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All **34 tests passed**. Coverage includes crop and resize geometry, the 1024/2048/4096/8192 square presets, portrait inversion, upscaling on/off, one-pass LANCZOS resizing, JPEG/PNG/TGA export, PNG/TGA alpha, metadata and color handling, English/French/Japanese UI, Dark/Light/Classic themes, language and theme persistence, stable panel geometry, emphasized dropdowns, Classic-only pixel icons, themed toggles, GPL footer, GitHub link dispatch, output-folder timing, input discovery, Qt drag and drop, preview dimensions, worker batches, and Windows distribution configuration. A dedicated matrix verifies that 1:1, 4:3, and 16:9 exports in JPEG, PNG, and TGA all use `PhotoCrop_Export`.

New exports are written beside each source folder under `PhotoCrop_Export`. Collision suffixing remains active, source originals remain untouched, and both the current directory and legacy `4x3_cropped` directories are excluded from recursive discovery. The batch completion test confirms that Explorer receives the first processed group's `PhotoCrop_Export` path once, after processing finishes.

The centered crop and preview geometry remain shared, and every requested resize still uses one direct LANCZOS pass.

## Frozen executable

`PhotoCropV2.exe` was built from the versioned `PhotoCropV2.spec` as a one-file windowed application. Its explicit `--self-test` completed with exit code 0 and reported:

- `passed: true`
- `frozen: true`
- version `2.2.2`
- bundled application icon found
- Qt plugin directory found
- no external Python required

The frozen self-test verified the three languages, three themes, footer, and GitHub target. Its five processing batches produced the expected landscape and portrait outputs in JPEG, PNG, and TGA and continued correctly after a deliberately corrupt input.

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

Inno Setup produced `dist\PhotoCrop_Setup.exe` with English, French, and Japanese choices. A fresh choice initializes the application language through its normal persisted setting. The installer was tested with a silent isolated installation under the system temporary directory, without using the development virtual environment. The installed `PhotoCropV2.exe` passed the same frozen self-test, the uninstaller was present, and silent uninstallation removed the test installation directory completely.

## Visual review

Native Windows captures were generated for empty and populated/preview states in all three themes. The reviewed combinations were Dark/English, Light/French, and Classic/Japanese. Additional Light captures verify the focused dropdown and its open menu. Header controls, settings, file list, preview, progress, status, log, and footer retain stable alignment between empty and populated states. Classic uses its own original low-color pixel icons; Dark and Light continue to use the modern Qt/Windows set.

Inno Setup is required only on the development machine to compile the installer. It is not installed or invoked on an end-user machine.

Generated executables, installers, reports, screenshots, caches, virtual environments, and local backups remain excluded from Git.
