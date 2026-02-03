# -*- mode: python ; coding: utf-8 -*-
"""
Lele - PyInstaller Spec File

Usage:
    # Version CPU (légère, ~500 MB):
    pip install -r requirements-cpu.txt
    pyinstaller lele.spec

    # Version CUDA (GPU, ~2.5 GB):
    pip install -r requirements-cuda.txt
    pyinstaller lele.spec
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Détecter si CUDA est disponible
try:
    import torch
    has_cuda = torch.cuda.is_available()
    torch_version = torch.__version__
except ImportError:
    has_cuda = False
    torch_version = "unknown"

print(f"Building Lele with PyTorch {torch_version}, CUDA: {has_cuda}")

# Collecter les données Whisper (modèles, assets)
whisper_datas = collect_data_files('whisper')

# Collecter les données imageio-ffmpeg (binaires FFmpeg)
ffmpeg_datas = collect_data_files('imageio_ffmpeg')

# Collecter tous les submodules torch (résout les erreurs d'import circulaire)
torch_imports = collect_submodules('torch')
torchaudio_imports = collect_submodules('torchaudio')

# Modules cachés nécessaires
hidden_imports = [
    'whisper',
    'numpy',
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'PIL',
    'PIL._tkinter_finder',
    'matplotlib',
    'matplotlib.backends.backend_tkagg',
    'networkx',
    'wordcloud',
    'pandas',
    'openpyxl',
    'mutagen',
    'psutil',
    # Auto-codage
    'sentence_transformers',
    'umap',
    'hdbscan',
    'sklearn',
    'sklearn.neighbors',
    'sklearn.cluster',
    # Torch submodules critiques
    *torch_imports,
    *torchaudio_imports,
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        *whisper_datas,
        *ffmpeg_datas,
        # Ajouter d'autres ressources si nécessaire
        # ('lele/resources', 'lele/resources'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclure les modules non nécessaires pour réduire la taille
        'tkinter.test',
        'unittest',
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
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
    name='Lele',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False = GUI app (pas de console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='lele/resources/icon.ico' if Path('lele/resources/icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Lele',
)
