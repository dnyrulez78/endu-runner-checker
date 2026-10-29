# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Percorso base assoluto
BASE_DIR = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(BASE_DIR, 'frontend'), 'frontend'),
    (os.path.join(BASE_DIR, 'assets', 'icon.ico'), 'assets'),
]

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespans',
    'uvicorn.lifespans.on',
    'uvicorn.lifespans.off',
    'webview',
    'webview.platforms',
    'webview.platforms.winforms',
    'clr',
    'pythonnet',
    'clr_loader',
    'httpx',
    'fastapi',
    'starlette',
    'pydantic',
    'cryptography',
    'cryptography.hazmat.primitives.asymmetric.ed25519',
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'sqlite3', 'unittest'],
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
    name='RunnerScanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BASE_DIR, 'assets', 'icon.ico'),
    version=os.path.join(BASE_DIR, 'version_info.txt') if os.path.exists(os.path.join(BASE_DIR, 'version_info.txt')) else None,
)
