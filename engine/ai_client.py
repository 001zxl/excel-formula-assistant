"""AI 客户端 — DeepSeek API (Anthropic Messages 兼容端点)。"""

import json
import logging
import httpx
from config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_FAST_MODEL,
    MAX_TOKENS,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class FormulaAIClient:
    """DeepSeek API 客户端，使用 Anthropic Messages 格式。"""

    def __init__(
        self,
        base_url: str = DEEPSEEK_BASE_URL,
        api_key: str = DEEPSEEK_API_KEY,
        model: str = DEEPSEEK_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.fast_model = DEEPSEEK_FAST_MODEL

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def generate_formula(
        self,
        system_prompt: str,
        user_request: str,
        use_fast: bool = False,
    ) -> dict:
        """调用 LLM 生成公式。

        Args:
            system_prompt: 系统提示词
            user_request: 用户请求
            use_fast: 是否使用快速模型（deepseek-v4-flash）

        Returns:
            {formula, explanation_zh, confidence, alternative_formulas, warnings, dependencies, raw_response}
        """
        model = self.fast_model if use_fast else self.model

        payload = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_request}
            ],
        }

        logger.info(f"Calling {model} at {self.base_url}/v1/messages")

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=self._headers(),
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text[:500]}")
                return {
                    "formula": "",
                    "explanation_zh": f"API 调用失败（{response.status_code}）",
                    "confidence": "low",
                    "alternative_formulas": [],
                    "warnings": [f"API error: {response.status_code}"],
                    "dependencies": [],
                    "raw_response": response.text[:1000],
                    "error": True,
                }

            data = response.json()
            return self._parse_response(data)

    def generate_formula_sync(
        self,
        system_prompt: str,
        user_request: str,
        use_fast: bool = False,
    ) -> dict:
        """同步版本的 generate_formula（用于非异步场景）。"""
        import asyncio
        return asyncio.run(
            self.generate_formula(system_prompt, user_request, use_fast)
        )

    def _parse_response(self, data: dict) -> dict:
        """解析 Anthropic Messages API 响应。"""
        raw_text = ""
        try:
            # Anthropic Messages 格式
            content = data.get("content", [])
            if isinstance(content, list) and content:
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        raw_text += block.get("text", "")
            elif isinstance(content, str):
                raw_text = content

            # 尝试提取 JSON
            json_text = self._extract_json(raw_text)
            result = json.loads(json_text)

            return {
                "formula": result.get("formula", ""),
                "explanation_zh": result.get("explanation_zh", ""),
                "confidence": result.get("confidence", "medium"),
                "alternative_formulas": result.get("alternative_formulas", []),
                "warnings": result.get("warnings", []),
                "dependencies": result.get("dependencies", []),
                "raw_response": raw_text,
                "error": False,
            }
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse response: {e}")
            return {
                "formula": "",
                "explanation_zh": "无法解析 AI 返回的公式",
                "confidence": "low",
                "alternative_formulas": [],
                "warnings": [f"响应解析失败: {str(e)}"],
                "dependencies": [],
                "raw_response": raw_text,
                "error": True,
            }

    @staticmethod
    def _extract_json(text: str) -> str:
        """从文本中提取 JSON 块。"""
        # 尝试找到 JSON 块
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start) if "```" in text[start:] else len(text)
            return text[start:end].strip()

        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start) if "```" in text[start:] else len(text)
            return text[start:end].strip()

        # 尝试找到 { 和 }
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            return text[brace_start : brace_end + 1]

        return text.strip()
