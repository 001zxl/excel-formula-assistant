"""本地代理服务器 — 连接 Excel 插件与 DeepSeek API。

运行在 localhost:8100，持有 API key。
插件通过此代理调用 AI，密钥不暴露在浏览器端。

用法:
  source .venv/bin/activate
  python local_proxy/server.py
"""

import sys
import json
import logging
from pathlib import Path

# 确保项目根在 path 中
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.prompt_builder import build_system_prompt, build_user_message
from engine.context_extractor import SheetContext
from engine.ai_client import FormulaAIClient
from engine.response_parser import parse_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("proxy")

app = FastAPI(title="Excel Formula AI Proxy")

# CORS — 允许来自 Excel 插件 (localhost:3000) 的请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = FormulaAIClient()


class FormulaRequest(BaseModel):
    request: str
    sheet_context: str = ""
    sheet_name: str = ""
    header_row: int = 1
    first_data_row: int = 2
    last_data_row: int = 100
    use_fast: bool = False


@app.get("/health")
async def health():
    return {"status": "ok", "model": ai_client.model}


@app.post("/api/generate-formula")
async def generate_formula(req: FormulaRequest):
    """接收插件发送的自然语言请求，返回生成的公式。"""
    logger.info(f"Generate: '{req.request[:80]}...' on {req.sheet_name}")

    # 构建简化的上下文（插件已提取，这里做二次处理）
    system_prompt = _build_prompt_from_frontend(req)
    user_message = req.request

    try:
        raw = ai_client.generate_formula_sync(
            system_prompt=system_prompt,
            user_request=user_message,
            use_fast=req.use_fast,
        )
        result = parse_response(raw)

        response = {
            "formula": result.formula,
            "explanation_zh": result.explanation_zh,
            "confidence": result.confidence,
            "alternative_formulas": result.alternative_formulas,
            "warnings": result.warnings,
            "dependencies": result.dependencies,
            "error": result.error,
        }

        logger.info(f"Generated: {result.formula}")
        return response

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


def _build_prompt_from_frontend(req: FormulaRequest) -> str:
    """根据前端传来的上下文信息构建系统提示词。"""
    parts = [
        "你是一个 Excel 公式专家。将用户的自然语言计算需求转换为正确的 Excel 公式。",
        "",
        "--- 输出格式 ---",
        "必须严格返回 JSON:",
        '{',
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


if __name__ == "__main__":
    import uvicorn

    _cert_dir = Path(__file__).resolve().parent
    _cert = str(_cert_dir / "cert.pem")
    _key = str(_cert_dir / "key.pem")

    logger.info("Starting Excel Formula AI Proxy on https://localhost:8100")
    logger.info(f"Model: {ai_client.model}")

    if Path(_cert).exists() and Path(_key).exists():
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8100,
            ssl_keyfile=_key,
            ssl_certfile=_cert,
            log_level="info",
        )
    else:
        logger.warning("SSL certs not found, running without HTTPS")
        uvicorn.run(app, host="127.0.0.1", port=8100, log_level="info")
