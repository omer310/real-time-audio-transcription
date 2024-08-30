import os
from PyInstaller.utils.hooks import collect_data_files

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['Live.py'],
    pathex=[],
    binaries=[],
    datas=[('README.md', '.'), ('requirements.txt', '.'), ('modules', 'modules')],
    hiddenimports=['soundcard'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AudioTranscriber',
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
    distpath='D:/AudioTranscriber_build',
    icon='icon.ico'  
)