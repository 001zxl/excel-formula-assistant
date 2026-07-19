"""合并单元格处理。

读取合并区域信息，并在内存中 fill-down 以便数据分析。
注意：不修改原始文件，只返回处理后的数据。
"""

from openpyxl.worksheet.worksheet import Worksheet


def get_merged_regions(ws: Worksheet) -> list[dict]:
    """获取工作表中所有合并单元格区域的信息。

    返回列表，每项：{min_row, min_col, max_row, max_col, top_left_value, description}
    """
    regions = []
    for merged_range in ws.merged_cells.ranges:
        top_left = ws.cell(
            row=merged_range.min_row, column=merged_range.min_col
        ).value
        regions.append(
            {
                "min_row": merged_range.min_row,
                "min_col": merged_range.min_col,
                "max_row": merged_range.max_row,
                "max_col": merged_range.max_col,
                "top_left_value": top_left,
                "description": f"{merged_range}: '{top_left}'",
            }
        )
    return regions


def fill_merged_values(ws: Worksheet, data_rows: list[list]) -> list[list]:
    """在内存中向下填充合并单元格的值。

    检测连续的空值（暗示来自合并），用上方非空值填充。
    """
    if not data_rows:
        return data_rows

    filled = [row[:] for row in data_rows]

    for col_idx in range(len(filled[0]) if filled else 0):
        last_value = None
        for row_idx in range(len(filled)):
            if col_idx < len(filled[row_idx]):
                val = filled[row_idx][col_idx]
                if val is not None and val != "":
                    last_value = val
                elif last_value is not None:
                    # 可能是合并导致空值 → 填充上方的值
                    filled[row_idx][col_idx] = last_value

    return filled
