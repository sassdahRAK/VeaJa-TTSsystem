# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Veaja
# Run: pyinstaller veaja.spec

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files
datas = [
    ('assets',   'assets'),
    ('styles',   'styles'),
    ('i18n',     'i18n'),
    ('config',   'config'),
]

# Collect edge-tts and pyttsx3 submodules
hiddenimports = [
    'edge_tts',
    'pyttsx3',
    'pyttsx3.drivers',
    'pyttsx3.drivers.espeak',
    'pyttsx3.drivers.sapi5',
    'pyttsx3.drivers.nsss',
    'pygame',
    'pygame.mixer',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'pyperclip',
    'PyQt6.QtSvg',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='veaja',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/veaja.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='veaja',
)
