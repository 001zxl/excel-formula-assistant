# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Excel 公式助手 (macOS / Windows)。"""

import sys
from pathlib import Path

# SPECPATH 是 PyInstaller 内置变量，指向 .spec 文件所在目录
_PROJECT_ROOT = Path(SPECPATH).resolve().parent  # excel-formula-assistant/
_DESKTOP_DIR = Path(SPECPATH).resolve()           # excel-formula-assistant/desktop/

_IS_MAC = sys.platform == "darwin"
_IS_WIN = sys.platform == "win32"

a = Analysis(
    [str(_DESKTOP_DIR / "app.py")],
    pathex=[str(_PROJECT_ROOT), str(_DESKTOP_DIR)],
    binaries=[],
    datas=[
        # React 静态文件
        (str(_DESKTOP_DIR / "static"), "static"),
        # 设置页面
        (str(_DESKTOP_DIR / "settings.html"), "."),
        # manifest 文件
        (str(_PROJECT_ROOT / "addin" / "manifest.xml"), "."),
        # 图标（托盘用）
        (str(_DESKTOP_DIR / "icon.png"), "."),
    ],
    hiddenimports=[x for x in [
        "fastapi",
        "uvicorn",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "httpx",
        "openpyxl",
        "rumps" if _IS_MAC else None,
        "pystray" if _IS_WIN else None,
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "engine",
        "engine.formula_catalog",
        "engine.context_extractor",
        "engine.header_detector",
        "engine.merge_handler",
        "engine.type_detector",
        "engine.prompt_builder",
        "engine.ai_client",
        "engine.response_parser",
        "config",
    ] if x is not None],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- 平台差异化配置 ---
if _IS_MAC:
    _icon_path = str(_DESKTOP_DIR / "icon.icns")
    _console = False
    _bundle_identifier = "com.excelformula.assistant"
    _info_plist = {
        "NSHighResolutionCapable": True,
        "LSUIElement": True,
        "CFBundleName": "Excel公式助手",
        "CFBundleDisplayName": "Excel 公式助手",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHumanReadableCopyright": "AI Excel Formula Assistant",
        "NSAppTransportSecurity": {
            "NSAllowsLocalNetworking": True,
        },
    }
elif _IS_WIN:
    _icon_path = str(_DESKTOP_DIR / "icon.png")
    _console = True  # 显示控制台窗口，便于排查防火墙/端口问题
    _bundle_identifier = None
    _info_plist = None
else:
    _icon_path = None
    _console = False
    _bundle_identifier = None
    _info_plist = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ExcelFormulaAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=_console,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_path,
)

# macOS: 额外打包为 .app bundle
if _IS_MAC:
    app = BUNDLE(
        exe,
        name="ExcelFormulaAI.app",
        icon=_icon_path,
        bundle_identifier=_bundle_identifier,
        info_plist=_info_plist,
    )
