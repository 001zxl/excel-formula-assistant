"""全局配置 — 从环境变量读取，不硬编码密钥。"""

import os
import json
from pathlib import Path

# --- JSON 配置文件回退（桌面应用用） ---
_CONFIG_DIR = Path.home() / ".excel-formula-assistant"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


def _load_api_key_from_file() -> str:
    """从配置文件读取 API Key（桌面应用通过 /settings 页面写入）。"""
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            return data.get("api_key", "")
        except (json.JSONDecodeError, IOError):
            return ""
    return ""


def save_api_key_to_file(api_key: str) -> None:
    """保存 API Key 到配置文件。"""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(
        json.dumps({"api_key": api_key}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_config_dir() -> Path:
    """返回配置目录（用于 SSL 证书等数据文件）。"""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return _CONFIG_DIR


# DeepSeek API（Anthropic 兼容端点）
DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com/anthropic",
)
# 优先级：DEEPSEEK_API_KEY > ANTHROPIC_AUTH_TOKEN > 配置文件
DEEPSEEK_API_KEY = (
    os.getenv("DEEPSEEK_API_KEY")
    or os.getenv("ANTHROPIC_AUTH_TOKEN")
    or _load_api_key_from_file()
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_FAST_MODEL = os.getenv("DEEPSEEK_FAST_MODEL", "deepseek-v4-flash")

# AI 调用参数
MAX_TOKENS = int(os.getenv("FORMULA_MAX_TOKENS", "1024"))
REQUEST_TIMEOUT = int(os.getenv("FORMULA_REQUEST_TIMEOUT", "60"))

# 上下文提取
MAX_HEADER_SCAN_ROWS = 30
MAX_SAMPLE_VALUES = 50

# 公式目录
CATALOG_TOP_K = 5  # prompt 中注入的匹配函数数量
