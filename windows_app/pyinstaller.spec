# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building the Windows executable."""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

fitz_data = collect_all("fitz")


a = Analysis(
    ["windows_app/windows_main.py"],
    pathex=[],
    binaries=fitz_data[1],
    datas=fitz_data[0],
    hiddenimports=fitz_data[2],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=False,
    name="pdf-merge",
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pdf-merge",
)
