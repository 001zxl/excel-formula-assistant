"""统一桌面服务器 — 同时服务 React 前端 + AI API 代理。

运行在 localhost:8100 (HTTPS)，一个端口解决所有需求：
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
async def generate_formula(req: FormulaRequest):
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


def run_server(host: str = "127.0.0.1", port: int | None = None) -> int:
    """启动 FastAPI 服务器（HTTPS）。返回实际端口号。

    证书自动生成（首次启动），保存在 ~/.excel-formula-assistant/。
    """
    import uvicorn

    if port is None:
        port = _find_free_port()

    config_dir = get_config_dir()
    cert_file = config_dir / "cert.pem"
    key_file = config_dir / "key.pem"

    if not cert_file.exists() or not key_file.exists():
        _generate_self_signed_cert(cert_file, key_file)

    logger.info(f"Starting server on https://{host}:{port}")
    logger.info(f"Static files: {_STATIC_DIR}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_keyfile=str(key_file),
        ssl_certfile=str(cert_file),
        log_level="info",
    )
    return port


def _generate_self_signed_cert(cert_path: Path, key_path: Path) -> None:
    """生成自签名 SSL 证书。"""
    import subprocess

    logger.info("Generating self-signed SSL certificate...")
    cert_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key_path),
            "-out", str(cert_path),
            "-days", "3650",
            "-nodes",
            "-subj", "/CN=localhost/O=ExcelFormulaAI",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    key_path.chmod(0o600)
    logger.info(f"SSL cert created: {cert_path}")


if __name__ == "__main__":
    run_server()
