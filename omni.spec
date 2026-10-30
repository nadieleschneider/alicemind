from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_dir = Path(SPECPATH)
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all(
    "streamlit"
)
datas = streamlit_datas + [
    (str(project_dir / "app.py"), "."),
    (str(project_dir / "agent_core.py"), "."),
    (str(project_dir / "agent_executor.py"), "."),
    (str(project_dir / ".streamlit" / "config.toml"), ".streamlit"),
]
binaries = streamlit_binaries
hiddenimports = streamlit_hiddenimports + [
    "resume_pdf",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "pypdf",
    "pypdf.errors",
    "tkinter",
    "tkinter.font",
    "tkinter.ttk",
]

analysis = Analysis(
    [str(project_dir / "omni_launcher.py")],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "llvmlite",
        "numba",
        "scipy",
        "sklearn",
        "sympy",
        "torch",
        "torchaudio",
        "torchvision",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="AliceMind",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AliceMind",
)
