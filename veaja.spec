# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Veaja
# Run: pyinstaller veaja.spec --clean --noconfirm

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Data files bundled into the exe ──────────────────────────────────────────
datas = [
    ('assets',   'assets'),
    ('styles',   'styles'),
    ('i18n',     'i18n'),
    ('config',   'config'),
]

# ── Hidden imports not auto-detected by PyInstaller ──────────────────────────
hiddenimports = [
    # TTS — online
    'edge_tts',
    'edge_tts.communicate',
    'edge_tts.list_voices',
    # TTS — offline
    'pyttsx3',
    'pyttsx3.drivers',
    'pyttsx3.drivers.espeak',
    'pyttsx3.drivers.sapi5',
    'pyttsx3.drivers.nsss',
    # Windows SAPI5 COM (used by our offline WAV-render path)
    'comtypes',
    'comtypes.client',
    'comtypes.server',
    'comtypes.typeinfo',
    # Audio
    'pygame',
    'pygame.mixer',
    # Input / clipboard
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'pynput._util',
    'pynput._util.win32',
    'pyperclip',
    # Qt
    'PyQt6.QtSvg',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    # Async (used by edge-tts)
    'asyncio',
    'aiohttp',
    'aiohttp.connector',
    # Misc
    'certifi',
    'tabulate',
    'winreg',
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
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy',
        'IPython', 'jupyter', 'notebook',
        'test', 'unittest',
    ],
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
    name='Veaja',
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
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Veaja',
)
