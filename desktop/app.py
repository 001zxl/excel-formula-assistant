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
    print(f"正在启动服务器: https://127.0.0.1:{port}")
    from desktop.server import run_server
    try:
        run_server(host="127.0.0.1", port=port)
    except Exception as e:
        # 弹出错误提示（跨平台）
        try:
            import tkinter.messagebox as mb
            mb.showerror(
                "Excel 公式助手 - 启动失败",
                f"服务启动失败:\n{e}\n\n"
                f"可能原因:\n"
                f"1. 端口 {port} 被占用\n"
                f"2. Windows 防火墙拦截（请点击「允许访问」）\n"
                f"3. 杀毒软件拦截\n\n"
                f"请尝试重启应用或更换端口。"
            )
        except Exception:
            pass


def _configure_windows_firewall():
    """尝试添加 Windows 防火墙例外（管理员权限下自动添加，否则给出指引）。"""
    if sys.platform != "win32":
        return
    import subprocess
    import ctypes

    # 检查是否以管理员身份运行
    is_admin = False
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        pass

    print(f"[防火墙] 管理员权限: {'是' if is_admin else '否（首次运行请在弹出的安全对话框中点击「允许访问」）'}")

    try:
        result = subprocess.run(
            'netsh advfirewall firewall show rule name="Excel公式助手"',
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if "未找到" not in result.stdout and "No rules match" not in result.stdout:
            print("[防火墙] 规则已存在，跳过")
            return

        if is_admin:
            exe_path = sys.executable
            r = subprocess.run(
                f'netsh advfirewall firewall add rule name="Excel公式助手" dir=in action=allow program="{exe_path}" enable=yes',
                shell=True, capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                print("[防火墙] 规则已自动添加")
            else:
                print(f"[防火墙] 添加失败: {r.stderr.strip()}")
        else:
            print("[防火墙] 当前非管理员，无法自动添加防火墙规则")
            print("[防火墙] Windows 安全警报弹出时请点击「允许访问」或「取消」不影响使用")
    except Exception as e:
        print(f"[防火墙] 配置异常（非致命）: {e}")


def _check_port_accessible(port: int, timeout: float = 3.0) -> bool:
    """验证端口是否已启动并监听。"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result == 0
    except Exception:
        return False


def _install_cert_trust():
    """将自签名证书添加到系统信任库（避免浏览器和 Excel 拦截）。"""
    from pathlib import Path
    cert_path = Path.home() / ".excel-formula-assistant" / "cert.pem"
    if not cert_path.exists():
        return

    if sys.platform == "darwin":
        import subprocess
        try:
            subprocess.run(
                ["security", "add-trusted-cert", "-d", "-r", "trustRoot",
                 "-k", str(Path.home() / "Library" / "Keychains" / "login.keychain-db"),
                 str(cert_path)],
                capture_output=True, timeout=10,
            )
            print("[证书] 已添加到 macOS 钥匙串信任库")
        except Exception as e:
            print(f"[证书] macOS 信任添加失败（非致命）: {e}")

    elif sys.platform == "win32":
        import subprocess
        try:
            r = subprocess.run(
                ["certutil", "-addstore", "-user", "Root", str(cert_path)],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                print("[证书] 已添加到 Windows 受信任根证书")
            else:
                print(f"[证书] Windows 信任添加失败: {r.stderr.strip()}")
        except Exception as e:
            print(f"[证书] Windows 信任添加异常（非致命）: {e}")


# ====================================================================
# macOS — rumps 菜单栏应用
# ====================================================================

def _run_mac_tray(port: int):
    import rumps
    from desktop.server import _ensure_ssl_cert

    # 确保证书存在 + 添加到系统信任库
    _ensure_ssl_cert()
    _install_cert_trust()

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
            _open_url(f"https://localhost:{self._port}/settings")

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
                    "服务器: https://localhost:8100\n\n"
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
    from desktop.server import _ensure_ssl_cert

    _configure_windows_firewall()

    # 确保证书存在 + 添加到系统信任库
    _ensure_ssl_cert()
    _install_cert_trust()

    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()
    import time; time.sleep(3)  # Windows 启动较慢，多等等

    if _check_port_accessible(port):
        print(f"[启动] 服务器已就绪: https://localhost:{port}")
    else:
        print(f"[启动] 警告: 端口 {port} 无法访问，可能是防火墙或杀毒软件拦截")
        print(f"[启动] 请检查 Windows 安全中心，允许 ExcelFormulaAI.exe 通过防火墙")

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
        pystray.MenuItem("打开设置…", lambda: _open_url(f"https://localhost:{port}/settings"), default=True),
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
