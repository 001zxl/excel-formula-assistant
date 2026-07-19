"""跨平台系统托盘应用 — Excel 公式助手 (macOS / Windows)。

- macOS: 使用 rumps（原生菜单栏）
- Windows: 使用 pystray
"""

import sys
import os
import threading
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

_IS_MAC = sys.platform == "darwin"


def _get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return _PROJECT_ROOT


def _find_manifest() -> Path | None:
    app_dir = _get_app_dir()
    candidates = [
        app_dir / "manifest.xml",
        app_dir / "desktop" / "manifest.xml",
        _PROJECT_ROOT / "addin" / "manifest.xml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _open_url(url: str):
    import webbrowser
    webbrowser.open(url)


def _open_file_location(path: Path):
    if not _IS_MAC:
        os.startfile(str(path.parent))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)])
    else:
        subprocess.run(["xdg-open", str(path.parent)])


def _check_api_key() -> bool:
    from config import DEEPSEEK_API_KEY
    return bool(DEEPSEEK_API_KEY)


def _start_server(port: int):
    from desktop.server import run_server
    run_server(host="127.0.0.1", port=port)


# ====================================================================
# macOS — rumps 菜单栏应用
# ====================================================================

def _run_mac_tray(port: int):
    import rumps

    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    class ExcelFormulaApp(rumps.App):
        def __init__(self):
            icon_path = _get_app_dir() / "icon.png"
            if not icon_path.exists():
                icon_path = _PROJECT_ROOT / "desktop" / "icon.png"
            icon = str(icon_path) if icon_path.exists() else None
            super().__init__(
                name="Excel 公式助手",
                title=None,
                icon=icon,
                template=False,
            )
            self._port = port

        @rumps.timer(3)
        def _update_title(self, _):
            try:
                configured = _check_api_key()
                self.title = "🟢" if configured else "🔴"
            except Exception:
                self.title = "⚪"

        @rumps.clicked("打开设置…")
        def open_settings(self, _):
            _open_url(f"http://localhost:{self._port}/settings")

        @rumps.clicked("在 Excel 中加载插件")
        def load_addin(self, _):
            manifest = _find_manifest()
            if manifest:
                _open_file_location(manifest)

        @rumps.clicked("关于 Excel 公式助手")
        def about(self, _):
            try:
                import tkinter.messagebox as mb
                configured = _check_api_key()
                mb.showinfo(
                    "关于 Excel 公式助手 v1.0",
                    "AI 驱动的 Excel 公式生成工具\n\n"
                    f"API Key: {'✅ 已配置' if configured else '⚠️ 未配置'}\n"
                    "服务器: http://localhost:8100\n\n"
                    "在 Excel 侧边栏中用自然语言描述需求，AI 自动生成公式。",
                )
            except Exception:
                pass

    ExcelFormulaApp().run()


# ====================================================================
# Windows — pystray 托盘应用
# ====================================================================

def _run_win_tray(port: int):
    import pystray

    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()
    import time; time.sleep(2)

    def _load_icon():
        from PIL import Image as PILImage, ImageDraw
        app_dir = _get_app_dir()
        icon_path = app_dir / "icon.png"
        if icon_path.exists():
            return PILImage.open(icon_path).resize((32, 32), PILImage.LANCZOS)
        img = PILImage.new("RGBA", (32, 32), (47, 84, 150, 255))
        draw = ImageDraw.Draw(img)
        draw.text((5, 6), "fx", fill="white")
        return img

    def _noop():
        pass

    menu = pystray.Menu(
        pystray.MenuItem("状态: " + ("✅ 已配置" if _check_api_key() else "⚠️ 未配置"), _noop, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("打开设置…", lambda: _open_url(f"http://localhost:{port}/settings"), default=True),
        pystray.MenuItem("在 Excel 中加载插件", lambda: _open_file_location(_find_manifest()) if _find_manifest() else None),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda icon: icon.stop()),
    )

    icon = pystray.Icon("ExcelFormulaAI", icon=_load_icon(), title="Excel 公式助手", menu=menu)
    icon.run()


# ====================================================================
# 入口
# ====================================================================

def run_tray(port: int = 8100):
    if _IS_MAC:
        _run_mac_tray(port)
    else:
        _run_win_tray(port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Excel 公式助手 — 桌面应用")
    parser.add_argument("--port", type=int, default=8100, help="服务器端口")
    parser.add_argument("--server-only", action="store_true", help="仅启动服务器（无系统托盘）")
    args = parser.parse_args()

    if args.server_only:
        _start_server(args.port)
    else:
        run_tray(args.port)
