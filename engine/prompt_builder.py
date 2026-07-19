"""系统提示词构建器。

组装发送给 LLM 的完整 prompt：
  固定指令 + 工作表上下文 + 匹配的函数目录 + 格式化规则 + 反幻觉护栏
"""

from engine.context_extractor import SheetContext
from engine.formula_catalog import search_functions, FunctionEntry
from config import CATALOG_TOP_K

SYSTEM_INSTRUCTION = """你是一个 Excel 公式专家。你的任务是将用户的自然语言计算需求转换为正确的 Excel 公式。

--- 输出格式 ---
你必须严格返回以下 JSON 格式（不要包含其他内容）：

{
  "formula": "=SUM(G5:G51)",
  "explanation_zh": "使用 SUM 函数计算 G5 到 G51 单元格的总和",
  "confidence": "high",
  "alternative_formulas": [],
  "warnings": [],
  "dependencies": []
}

字段说明：
- formula: 生成的 Excel 公式（以 = 开头，使用英文函数名）
- explanation_zh: 中文解释，说明公式做了什么
- confidence: "high"（非常确定）| "medium"（基本确定）| "low"（不确定，请人工审核）
- alternative_formulas: 其他可选的公式方案（数组）
- warnings: 使用该公式需要注意的事项（数组）
- dependencies: 公式成立的前提假设（数组）

--- 核心规则 ---
1. 使用英文函数名（这是 Excel 的实际公式语言）
2. 列引用使用字母（A、B、C...），不是数字序号
3. 如果用户提到列名（如"中位数"列、"薪资范围"列），请将其映射到正确的列字母
4. 绝不编造函数。只使用 Excel 内置的真实函数
5. 检查潜在问题（合并单元格、文本格式数字、数据范围等），在 warnings 中添加提示
6. 对于带千分位逗号的数字文本（如 "6,000"），提示或建议使用 VALUE(SUBSTITUTE(...,",","")) 转换
7. 如果用户请求无法用任何 Excel 内置函数满足，解释原因并建议最接近的替代方案
8. 引用范围要精确：从数据起始行到数据结束行"""


def build_system_prompt(
    ctx: SheetContext,
    user_request: str = "",
    extra_functions: list[FunctionEntry] | None = None,
) -> str:
    """构建完整的系统提示词。

    Args:
        ctx: 工作表上下文
        user_request: 用户的自然语言请求（用于匹配相关函数）
        extra_functions: 额外需要注入的函数条目
    """
    parts = [SYSTEM_INSTRUCTION]

    # 工作表上下文
    ctx_text = ctx.describe()
    parts.append(f"\n--- 当前工作表上下文 ---\n{ctx_text}")

    # 匹配相关函数
    if user_request:
        matched = search_functions(user_request, top_k=CATALOG_TOP_K)
        if extra_functions:
            matched.extend(extra_functions)
            # 去重
            seen = set()
            matched = [f for f in matched if not (f.name in seen or seen.add(f.name))]

        if matched:
            func_lines = ["\n--- 可能相关的函数 ---"]
            for func in matched:
                func_lines.append(
                    f"\n{func.name}({func.syntax.split('(', 1)[1] if '(' in func.syntax else ''}"
                    f"\n  中文名: {func.zh_name}"
                    f"\n  描述: {func.description_zh}"
                    f"\n  示例: {func.example_zh}"
                    f"\n  常见用例: {'、'.join(func.common_use_cases)}"
                )
                if func.pitfalls:
                    func_lines.append(f"  注意事项: {'; '.join(func.pitfalls)}")
            parts.append("\n".join(func_lines))

    # 格式化规则
    parts.append(
        """
--- 格式规则 ---
- 函数名使用英文（SUM 不是 求和）
- 参数分隔符使用逗号 ,
- 文本条件需要双引号，如 "一线"
- 范围引用格式：起始列字母+起始行号:结束列字母+结束行号，如 G5:G51
- 绝对引用用 $ 符号，如 $G$5:$G$51
- 数字中的逗号是千分位显示格式，公式中不需要"""
    )

    return "\n".join(parts)


def build_user_message(user_request: str, ctx: SheetContext | None = None) -> str:
    """构建用户消息。

    Args:
        user_request: 用户的自然语言请求
        ctx: 可选，附加目标单元格提示
    """
    return user_request
