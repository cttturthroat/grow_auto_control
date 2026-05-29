# grow_control.spec
# PyInstaller 6.x spec for the Grow Auto Control GUI application.
#
# Build:
#   poetry run pyinstaller grow_control.spec
#
# Output:
#   dist/grow_control/grow_control.exe   ← launch this
#   dist/grow_control/.env.example       ← copy to .env and edit before first run
#
# Distribution:
#   Zip the entire dist/grow_control/ folder and share it.
#   The end-user must place a .env file (copied from .env.example) next to the .exe.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# tzdata ships IANA timezone data files needed by zoneinfo on Windows.
tzdata_datas = collect_data_files('tzdata')

# pydantic uses dynamic validators that PyInstaller may not detect statically.
pydantic_hidden = collect_submodules('pydantic')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('.env.example', '.'),
        *tzdata_datas,
    ],
    hiddenimports=[
        # Serial communication
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        # Async Qt integration
        'qasync',
        # Logging
        'loguru',
        # Settings / validation
        'pydantic_settings',
        *pydantic_hidden,
        # Timezone data
        'tzdata',
        # Application packages (ensure all sub-modules are picked up)
        'app',
        'app.core',
        'app.core.config',
        'app.core.logging',
        'app.gui',
        'app.gui.main_window',
        'app.gui.widgets',
        'app.gui.widgets.actuator_panel',
        'app.gui.widgets.led_panel',
        'app.gui.widgets.log_panel',
        'app.gui.widgets.sensor_panel',
        'app.gui.widgets.settings_panel',
        'app.hardware',
        'app.hardware.base',
        'app.hardware.mock_board',
        'app.hardware.serial_board',
        'app.services',
        'app.services.controller',
        'app.services.led_scheduler',
        'app.services.settings_store',
        'app.utils',
        'app.utils.paths',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Only exclude modules that are genuinely unused; be conservative.
    # email/html/http are needed by importlib.metadata → pydantic chain.
    excludes=[
        'tkinter',
        '_tkinter',
        'test',
        'unittest',
        'doctest',
        'antigravity',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='grow_control',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        # Qt DLLs are already compressed; re-compressing wastes time / can break them.
        'Qt6*.dll',
        'PySide6*.pyd',
    ],
    runtime_tmpdir=None,
    # console=False → no terminal window; errors go to grow_control.log (next to exe).
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['Qt6*.dll', 'PySide6*.pyd'],
    name='grow_control',
)
