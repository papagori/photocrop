# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct,
    VSVersionInfo,
)

from cropper.version import __version__


version_numbers = tuple(int(part) for part in __version__.split('.')) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=version_numbers,
        prodvers=version_numbers,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo([
            StringTable('040904B0', [
                StringStruct('CompanyName', 'PhotoCrop'),
                StringStruct('FileDescription', 'PhotoCropV2 photo crop and resize utility'),
                StringStruct('FileVersion', __version__),
                StringStruct('InternalName', 'PhotoCropV2'),
                StringStruct('LegalCopyright', 'GNU General Public License v3.0'),
                StringStruct('OriginalFilename', 'PhotoCropV2.exe'),
                StringStruct('ProductName', 'PhotoCropV2'),
                StringStruct('ProductVersion', __version__),
            ]),
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/photocrop.ico', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PhotoCropV2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/photocrop.ico',
    version=version_info,
)
