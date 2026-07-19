"""路径解析 — 处理相对路径、~ 展开、文件存在性检查。"""

import os
from pathlib import Path


def resolve_path(file_path: str) -> Path:
    """解析文件路径：展开 ~、转为绝对路径、检查存在性。"""
    expanded = os.path.expanduser(file_path)
    path = Path(expanded).resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if not path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        raise ValueError(f"不支持的文件格式: {path.suffix}，仅支持 .xlsx/.xlsm/.xls")
    return path
