"""A1 单元格表示法解析。

支持：A1, $A$1, AB12, Sheet1!A1 等格式。
"""

import re

_CELL_RE = re.compile(r"^(\$?[A-Za-z]{1,3})(\$?\d{1,7})$")


def parse_cell(cell_ref: str) -> tuple[str, int]:
    """解析单元格引用，返回 (列字母, 行号)。

    >>> parse_cell("A1")
    ('A', 1)
    >>> parse_cell("$G$51")
    ('G', 51)
    >>> parse_cell("AB100")
    ('AB', 100)
    """
    cleaned = cell_ref.strip().replace("$", "")
    m = _CELL_RE.match(cleaned)
    if not m:
        raise ValueError(f"无效的单元格引用: {cell_ref}")
    return m.group(1).upper(), int(m.group(2))


def col_letter_to_index(col: str) -> int:
    """列字母 → 1-based 列号。A=1, Z=26, AA=27。"""
    result = 0
    for c in col.upper():
        result = result * 26 + (ord(c) - ord("A") + 1)
    return result
