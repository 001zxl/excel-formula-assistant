"""统一桌面服务器 — 同时服务 React 前端 + AI API 代理。

运行在 https://localhost:8100 (HTTPS)，一个端口解决所有需求：
  /                    → React 静态文件（Excel 侧边栏插件）
  /api/generate-formula → AI 公式生成
  /api/settings         → API Key 读写
  /health               → 健康检查
  /settings             → 配置页面（HTML）

开发模式下不依赖此文件——用 start.sh 启动独立服务。
"""

import sys
import json
import logging
import socket
from pathlib import Path

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from engine.prompt_builder import build_system_prompt, build_user_message
from engine.ai_client import FormulaAIClient
from engine.response_parser import parse_response
from config import DEEPSEEK_MODEL, save_api_key_to_file, get_config_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("desktop-server")

app = FastAPI(title="Excel Formula AI — Desktop Server")

# ---- 资源路径（兼容 PyInstaller 打包和开发模式） ----
def _get_resource_dir() -> Path:
    """返回资源根目录。打包后为 sys._MEIPASS，开发时为本文件所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


_RESOURCE_DIR = _get_resource_dir()
_STATIC_DIR = _RESOURCE_DIR / "static"
_SETTINGS_HTML = _RESOURCE_DIR / "settings.html"


# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================================================================
# API 数据模型
# ====================================================================


class FormulaRequest(BaseModel):
    request: str
    sheet_context: str = ""
    sheet_name: str = ""
    header_row: int = 1
    first_data_row: int = 2
    last_data_row: int = 100
    use_fast: bool = False


class SettingsRequest(BaseModel):
    api_key: str


# ====================================================================
# 路由
# ====================================================================


@app.get("/health")
async def health():
    """健康检查。AI 客户端延迟初始化。"""
    client = _get_ai_client()
    return {
        "status": "ok",
        "model": DEEPSEEK_MODEL,
        "configured": bool(client.api_key),
    }


@app.post("/api/generate-formula")
def generate_formula(req: FormulaRequest):
    """接收 Excel 插件发送的自然语言请求，返回生成的公式。"""
    logger.info(f"Generate: '{req.request[:80]}...' on {req.sheet_name}")

    system_prompt = _build_prompt(req)
    client = _get_ai_client()

    if not client.api_key:
        return JSONResponse(
            status_code=401,
            content={
                "formula": "",
                "explanation_zh": "未配置 API Key。请打开设置页面配置 DeepSeek API Key。",
                "confidence": "low",
                "alternative_formulas": [],
                "warnings": [],
                "dependencies": [],
                "error": True,
            },
        )

    try:
        raw = client.generate_formula_sync(
            system_prompt=system_prompt,
            user_request=req.request,
            use_fast=req.use_fast,
        )
        result = parse_response(raw)
        logger.info(f"Generated: {result.formula}")
        return {
            "formula": result.formula,
            "explanation_zh": result.explanation_zh,
            "confidence": result.confidence,
            "alternative_formulas": result.alternative_formulas,
            "warnings": result.warnings,
            "dependencies": result.dependencies,
            "error": result.error,
        }
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {
            "formula": "",
            "explanation_zh": f"生成失败: {str(e)}",
            "confidence": "low",
            "alternative_formulas": [],
            "warnings": [],
            "dependencies": [],
            "error": True,
        }


@app.get("/api/settings")
async def get_settings():
    """获取当前配置状态。"""
    client = _get_ai_client()
    return {
        "configured": bool(client.api_key),
        "api_key_preview": _mask_key(client.api_key) if client.api_key else "",
        "model": DEEPSEEK_MODEL,
    }


@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    """保存 API Key。"""
    key = req.api_key.strip()
    if not key:
        return JSONResponse(status_code=400, content={"ok": False, "message": "API Key 不能为空"})

    save_api_key_to_file(key)
    # 重新加载 AI 客户端
    _reload_ai_client()
    logger.info("API Key saved and client reloaded")
    return {"ok": True, "message": "API Key 已保存"}


# ====================================================================
# 静态页面
# ====================================================================


@app.get("/settings")
async def settings_page():
    """返回 API Key 配置页面。"""
    if _SETTINGS_HTML.exists():
        return FileResponse(_SETTINGS_HTML, media_type="text/html; charset=utf-8")
    return JSONResponse(status_code=404, content={"error": "settings.html not found"})


@app.get("/manifest.xml")
async def manifest_xml():
    """返回 Excel 侧边栏插件的 manifest 文件。"""
    manifest = _RESOURCE_DIR / "manifest.xml"
    if manifest.exists():
        return FileResponse(manifest, media_type="application/xml; charset=utf-8")
    return JSONResponse(status_code=404, content={"error": "manifest.xml not found"})


@app.get("/icon.png")
async def icon_png():
    """返回 App 图标（托盘 / Office 侧边栏使用）。"""
    icon = _STATIC_DIR / "icon.png"
    if not icon.exists():
        icon = _RESOURCE_DIR / "icon.png"
    if icon.exists():
        return FileResponse(icon, media_type="image/png")
    return JSONResponse(status_code=404, content={"error": "icon.png not found"})


# ====================================================================
# 辅助函数
# ====================================================================


_ai_client: FormulaAIClient | None = None


def _get_ai_client() -> FormulaAIClient:
    """延迟初始化 AI 客户端（优先从配置文件读取 Key）。"""
    global _ai_client
    if _ai_client is None:
        from config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL as model, _load_api_key_from_file
        api_key = _load_api_key_from_file()
        _ai_client = FormulaAIClient(base_url=DEEPSEEK_BASE_URL, api_key=api_key, model=model)
    return _ai_client


def _reload_ai_client() -> None:
    """重新加载 AI 客户端（API Key 变更后）。

    直接读取配置文件以避免 config 模块的缓存问题。
    """
    global _ai_client
    from config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL as model, _load_api_key_from_file

    api_key = _load_api_key_from_file()
    _ai_client = FormulaAIClient(
        base_url=DEEPSEEK_BASE_URL,
        api_key=api_key,
        model=model,
    )
    logger.info(f"AI client reloaded (key={'present' if api_key else 'missing'})")


def _mask_key(key: str) -> str:
    """脱敏显示 API Key。"""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _build_prompt(req: FormulaRequest) -> str:
    """根据前端传来的上下文信息构建系统提示词。"""
    parts = [
        "你是一个 Excel 公式专家。将用户的自然语言计算需求转换为正确的 Excel 公式。",
        "",
        "--- 输出格式 ---",
        "必须严格返回 JSON:",
        "{",
        '  "formula": "=SUM(G5:G51)",',
        '  "explanation_zh": "中文解释",',
        '  "confidence": "high|medium|low",',
        '  "alternative_formulas": [],',
        '  "warnings": [],',
        '  "dependencies": []',
        "}",
        "",
        "--- 规则 ---",
        "1. 使用英文函数名",
        "2. 列引用使用字母（A、B、C...）",
        "3. 如果用户提到列名，映射到正确的列字母",
        "4. 绝不编造不存在的函数",
        "5. 引用范围要精确（从数据起始行到结束行）",
        "",
        f"--- 工作表: {req.sheet_name} ---",
        f"表头在第{req.header_row}行，数据从第{req.first_data_row}行到第{req.last_data_row}行",
    ]

    if req.sheet_context:
        parts.append(req.sheet_context)

    return "\n".join(parts)


# ====================================================================
# 挂载 React 静态文件（必须在所有 API 路由之后）
# ====================================================================

if _STATIC_DIR.exists() and (_STATIC_DIR / "index.html").exists():
    # 挂载静态资源目录
    assets_dir = _STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def index_html():
        """返回 React 入口页面。"""
        return FileResponse(
            _STATIC_DIR / "index.html",
            media_type="text/html; charset=utf-8",
        )

    @app.get("/index.html")
    async def index_html_exact():
        """Excel 加载项请求的精确路径。"""
        return FileResponse(
            _STATIC_DIR / "index.html",
            media_type="text/html; charset=utf-8",
        )

    logger.info(f"Serving React static files from {_STATIC_DIR}")
else:
    logger.warning(f"Static dir not found or missing index.html: {_STATIC_DIR}")


# ====================================================================
# 启动
# ====================================================================


def _find_free_port(start: int = 8100, attempts: int = 4) -> int:
    """查找空闲端口。"""
    for offset in range(attempts):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start  # fallback


def _ensure_ssl_cert() -> tuple[Path, Path, Path]:
    """确保 CA 根证书 + 服务器证书都存在。返回 (ca_cert_path, server_cert_path, server_key_path)。

    采用 mkcert 模型：CA 根证书加入系统信任库一次，服务器证书由 CA 签发，
    浏览器/Excel 验证服务器证书时沿信任链找到 CA → 通过。
    """
    from config import get_config_dir

    cert_dir = get_config_dir()
    ca_key_path = cert_dir / "ca-key.pem"
    ca_cert_path = cert_dir / "ca-cert.pem"
    server_key_path = cert_dir / "key.pem"
    server_cert_path = cert_dir / "cert.pem"

    # 1. CA 根证书（长期有效，只生成一次）
    if not ca_key_path.exists() or not ca_cert_path.exists():
        # 迁移：删除旧的自签名证书（它们不是 CA 签发的，无法通过验证）
        for old in [server_cert_path, server_key_path, ca_key_path, ca_cert_path]:
            if old.exists():
                old.unlink()
                logger.info(f"已删除旧证书: {old.name}")
        _generate_ca_cert(ca_key_path, ca_cert_path)

    # 2. 服务器证书（由 CA 签发）
    #    以下情况重新生成：不存在 / CA 比服务器证书新
    regenerate = not server_key_path.exists() or not server_cert_path.exists()
    if not regenerate and ca_cert_path.stat().st_mtime > server_cert_path.stat().st_mtime:
        server_cert_path.unlink()
        server_key_path.unlink()
        regenerate = True
        logger.info("CA 已更新，重新签发服务器证书")

    if regenerate:
        _generate_server_cert(ca_key_path, ca_cert_path, server_key_path, server_cert_path)

    return ca_cert_path, server_cert_path, server_key_path


def _generate_ca_cert(ca_key_path: Path, ca_cert_path: Path) -> None:
    """生成本地 CA 根证书。该证书会被加入系统信任库。"""
    import datetime

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PrivateFormat, NoEncryption,
    )

    logger.info("生成 CA 根证书...")
    ca_key_path.parent.mkdir(parents=True, exist_ok=True)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "ExcelFormulaAI Local CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ExcelFormulaAI"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)  # 自签名
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=7300))  # 20 年
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                key_cert_sign=True,   # CA 必须：允许签发子证书
                crl_sign=True,        # CA 必须：允许签发吊销列表
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    ca_key_path.write_bytes(ca_key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
    ca_key_path.chmod(0o600)
    ca_cert_path.write_bytes(ca_cert.public_bytes(Encoding.PEM))
    logger.info(f"CA 根证书已创建: {ca_cert_path}")


def _generate_server_cert(
    ca_key_path: Path, ca_cert_path: Path,
    server_key_path: Path, server_cert_path: Path,
) -> None:
    """由 CA 签发 localhost 服务器证书。"""
    import datetime
    import ipaddress

    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PrivateFormat, NoEncryption,
    )

    logger.info("由 CA 签发 localhost 服务器证书...")

    # 加载 CA 私钥和证书
    ca_key = _load_private_key(ca_key_path.read_bytes())
    ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())

    # 生成服务器私钥
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ExcelFormulaAI"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)  # ← 由 CA 签发
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())  # ← CA 私钥签名
    )

    server_key_path.write_bytes(server_key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
    server_key_path.chmod(0o600)
    server_cert_path.write_bytes(server_cert.public_bytes(Encoding.PEM))
    logger.info(f"服务器证书已创建: {server_cert_path}")


def _load_private_key(data: bytes):
    """加载 PEM 格式私钥。"""
    from cryptography.hazmat.primitives.serialization import (
        NoEncryption,
    )
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key,
    )
    return load_pem_private_key(data, password=None)


def run_server(host: str = "127.0.0.1", port: int | None = None) -> int:
    """启动 FastAPI 服务器（HTTPS）。返回实际端口号。

    使用自签名证书 + 系统信任库自动注册，
    确保浏览器设置页和 Excel 侧边栏都能正常加载。
    """
    import uvicorn

    if port is None:
        port = _find_free_port()

    ca_cert_path, cert_path, key_path = _ensure_ssl_cert()
    logger.info(f"Starting server on https://{host}:{port}")
    logger.info(f"Static files: {_STATIC_DIR}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_keyfile=str(key_path),
        ssl_certfile=str(cert_path),
        log_level="info",
    )
    return port


if __name__ == "__main__":
    run_server()
