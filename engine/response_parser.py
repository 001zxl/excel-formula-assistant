"""AI 响应解析器 — 结构化验证和清洗。"""

from dataclasses import dataclass, field
from engine.formula_catalog import get_function_by_name


@dataclass
class FormulaResult:
    """AI 生成的公式结果。"""

    formula: str
    explanation_zh: str
    confidence: str  # "high" | "medium" | "low"
    alternative_formulas: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    raw_response: str = ""
    error: bool = False

    def to_dict(self) -> dict:
        return {
            "formula": self.formula,
            "explanation_zh": self.explanation_zh,
            "confidence": self.confidence,
            "alternative_formulas": self.alternative_formulas,
            "warnings": self.warnings,
            "dependencies": self.dependencies,
            "error": self.error,
        }

    def describe(self) -> str:
        """生成人类可读的描述。"""
        parts = [f"公式: {self.formula}"]
        if self.explanation_zh:
            parts.append(f"说明: {self.explanation_zh}")
        parts.append(f"置信度: {self.confidence}")
        if self.alternative_formulas:
            parts.append(f"备选方案: {', '.join(self.alternative_formulas)}")
        if self.warnings:
            parts.append("注意事项:")
            for w in self.warnings:
                parts.append(f"  ⚠ {w}")
        if self.dependencies:
            parts.append("使用前提:")
            for d in self.dependencies:
                parts.append(f"  - {d}")
        return "\n".join(parts)


def parse_response(raw: dict) -> FormulaResult:
    """将 AI 客户端的原始响应字典转为 FormulaResult。"""
    return FormulaResult(
        formula=raw.get("formula", ""),
        explanation_zh=raw.get("explanation_zh", ""),
        confidence=raw.get("confidence", "medium"),
        alternative_formulas=raw.get("alternative_formulas", []),
        warnings=raw.get("warnings", []),
        dependencies=raw.get("dependencies", []),
        raw_response=raw.get("raw_response", ""),
        error=raw.get("error", False),
    )


def validate_formula(formula: str) -> dict:
    """基本公式验证。

    检查项：
    - 是否以 = 开头
    - 函数名是否存在于目录中
    - 括号是否匹配
    """
    issues = []

    if not formula:
        return {"valid": False, "issues": ["公式为空"]}

    if not formula.startswith("="):
        issues.append("公式应以 = 开头")
        formula = "=" + formula

    # 括号匹配
    if formula.count("(") != formula.count(")"):
        issues.append(f"括号不匹配：( 有 {formula.count('(')} 个，) 有 {formula.count(')')} 个")

    # 检查引号配对
    if formula.count('"') % 2 != 0:
        issues.append("双引号未配对")

    # 提取函数名检查
    func_candidates = []
    for part in formula.split("("):
        if part:
            # 取最后一个非字母数字字符之后的部分
            name = ""
            for c in reversed(part):
                if c.isalpha() or c.isdigit() or c == ".":
                    name = c + name
                else:
                    break
            if name and name[0].isalpha():
                func_candidates.append(name.upper())

    for func_name in func_candidates:
        if func_name in ("IF", "SUM", "MAX", "MIN", "AND", "OR", "NOT", "TRUE", "FALSE"):
            continue  # 跳过常见基础函数
        if not get_function_by_name(func_name):
            issues.append(f"函数 {func_name} 未在目录中找到（可能不存在或未被收录）")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "normalized_formula": formula,
    }
