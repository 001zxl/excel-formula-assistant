"""列数据类型推断。

检测中文 Excel 文件中常见的非标准数据格式：
- 千分位逗号数字："6,000"
- 薪资范围文本："5,000-7,000"
- 日期格式文本
- 含数字的混合文本
"""

import re
from typing import Any


def detect_column_type(sample_values: list[Any]) -> str:
    """根据样本值推断列的数据类型。

    返回类型标签：
    - "empty": 全空
    - "numeric": 纯数值（int/float）
    - "numeric-with-comma": 带千分位逗号的数字文本如 "6,000"
    - "text-range": 范围文本如 "5,000-7,000"
    - "text-date": 日期格式文本
    - "text": 纯文本
    - "text-with-numbers": 含数字的混合文本
    - "mixed": 混合类型
    """
    non_null = [v for v in sample_values if v is not None and v != ""]
    if not non_null:
        return "empty"

    # 纯数值
    if all(isinstance(v, (int, float)) for v in non_null):
        return "numeric"

    # 全文本
    str_values = [str(v).strip() for v in non_null]
    all_str = all(isinstance(v, str) for v in non_null)

    if all_str:
        # 范围模式："5,000-7,000"、"5000-7000"、"5k-7k"
        range_count = sum(
            1
            for v in str_values
            if re.search(r"\d[\d,]*\s*[-~—]\s*\d[\d,]*", v)
        )
        if range_count / len(str_values) >= 0.3:
            return "text-range"

        # 纯千分位数字："6,000"、"12,500"
        comma_num_count = sum(
            1 for v in str_values if re.match(r"^\d{1,3}(,\d{3})*(\.\d+)?$", v)
        )
        if comma_num_count / len(str_values) >= 0.5:
            return "numeric-with-comma"

        # 日期模式
        date_count = sum(
            1
            for v in str_values
            if re.search(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", v)
            or re.search(r"^\d{1,2}[-/月]\d{1,2}[-/日]?", v)
        )
        if date_count / len(str_values) >= 0.5:
            return "text-date"

        return "text"

    # 混合：有些是数字有些是文本
    if any(isinstance(v, str) and re.search(r"\d", str(v)) for v in non_null):
        return "text-with-numbers"

    return "mixed"


def extract_sample_values(values: list[Any], max_samples: int = 50) -> list[Any]:
    """提取列的非空样本值。"""
    non_null = [v for v in values if v is not None and v != ""]
    return non_null[:max_samples]


def get_data_quality_note(col_name: str, col_type: str) -> str | None:
    """根据列类型生成数据质量提示，用于注入 prompt。"""
    notes = {
        "text-range": f'"{col_name}" 列包含范围文本（如"5,000-7,000"），需用 TEXTBEFORE/TEXTAFTER 或 MID 拆分后再计算',
        "numeric-with-comma": f'"{col_name}" 列的数字含千分位逗号（如"6,000"），需用 VALUE(SUBSTITUTE(...)) 清理后再运算',
        "text-date": f'"{col_name}" 列包含日期文本，需用 DATEVALUE 或 DATE 函数转换',
        "text-with-numbers": f'"{col_name}" 列混合文本和数字，需分别处理',
        "mixed": f'"{col_name}" 列数据类型不一致',
    }
    return notes.get(col_type)
