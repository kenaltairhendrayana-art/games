# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for OPERATION: IRON LINE.

    pyinstaller iron_line.spec

ONE FILE, because the whole game is one file. `dist/IronLine.exe` is a
single executable you can drop in a zip and hand to somebody.

There are NO `datas`. Every graphic in this game is drawn in code and all
eighteen pieces of music are generated in code, so there is nothing to
bundle, nothing to find at runtime, and nothing in the build that anybody
has to hold a licence for. That is also why there is no `_app_dir()` in
the source any more - a one-file build unpacks itself into a temp tree
that is deleted on exit, and the only thing that survives the process is
the player's profile, which `_save_dir()` puts in the OS data directory
instead.
"""

a = Analysis(
    ["iron_line.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # tkinter is the only big thing pygame never touches. Kept deliberately
    # short: every other exclusion saves a megabyte and risks an import
    # error a player sees and we do not.
    excludes=["tkinter"],
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
    name="IronLine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # A GAME, NOT A TERMINAL PROGRAM: no console window behind it. The
    # cost is that a crash before the window opens is invisible, so
    # `build.py --console` exists to rebuild with one when something is
    # wrong.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
