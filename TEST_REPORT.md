# PhotoCropV2 validation

Validated on Windows x64 with Python 3.10.6, Pillow 12.3.0, PySide6 6.11.0, and PyInstaller 6.20.0.

## Public release checks

Before publishing, the existing application was tested again without changing its functionality:

- **21 automated tests passed**, in 2.544 seconds.
- The explicit application self-test passed all three processing batches.
- The public README, dependency files, build instructions, and official GPL v3 license were checked.
- All historical tracked paths were audited, as well as current files. No generated images, executables, archives, virtual environments, or caches are included.
- Ignore rules were checked against 15 representative paths, including nested Python caches, build outputs, PyInstaller files, IDE files, environment files, and backup archives.

## Automated coverage

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers:

- Landscape, portrait, square, and already-correct images; exact maximal centered crop geometry.
- Every selectable aspect ratio, including normalization of 21:9 and 16:10.
- All output presets, portrait dimension reversal, rounding, and no-upscaling behavior.
- 4096 px examples: 4:3 → 4096 × 3072; 16:9 → 4096 × 2304; reversed dimensions for portrait.
- No resizing with Original Resolution, and very small images with No Crop.
- Exactly one LANCZOS resize after cropping, with intermediate reduction disabled.
- Upscaling decisions based on the cropped dimensions, rather than the original dimensions.
- All eight EXIF orientations, retained ICC data, updated final EXIF dimensions, and orientation-tag removal.
- JPEG quality settings, unchanged source file hashes, filename collisions, and separate output directories.
- PNG, TIFF, WEBP, JPEG, transparency, and filtered palette conversion.
- Unicode paths, recursive discovery, duplicate and output-folder exclusion.
- Corrupt files, unsupported multipage/high-bit-depth inputs, and continued batch processing after errors.
- Qt drag-and-drop events, settings synchronization, disabled controls during processing, and worker results.

## Compiled executable verification

The V2 executable was built using `--onefile --windowed --name PhotoCropV2` and verified with its explicit `--self-test` mode. The standalone process exited with code **0**, reporting `passed: true` and `frozen: true`.

| Compiled batch | Landscape output | Portrait output |
| --- | --- | --- |
| 16:9, 1024 px long edge, no upscaling | 592 × 333 | 333 × 592 |
| 16:9, 1024 px long edge, upscaling allowed | 1024 × 576 | 576 × 1024 |
| Exact 1200 × 800 preset, automatic 3:2 | 1200 × 800 | 800 × 1200 |

Each batch processed two valid images and reported one deliberately corrupt JPEG without interrupting the other images. Outputs were reopened and dimensions checked. Repeated batches also verified numbered output suffixes.

The self-test uses the actual Qt interface and worker with the offscreen platform plugin and temporary synthetic inputs. It does not simulate physical Windows clicks. Qt drag-and-drop events are covered separately by the source tests. GUI captures were visually inspected during development.

Test reports, screenshots, and compiled executables are generated locally and excluded from Git. See README.md for reproduction commands and documented format/rounding limitations.
