import React from "react";
import type { SheetContext } from "../types";

interface Props {
  context: SheetContext | null;
}

export default function SheetContextPanel({ context }: Props) {
  if (!context) {
    return <div className="sheet-context empty">未检测到工作表，请在 Excel 中打开数据</div>;
  }

  return (
    <div className="sheet-context">
      <div className="sc-header">
        📊 {context.sheetName}
        <span className="sc-meta">
          表头第{context.headerRow}行 · {context.totalRows}行数据
        </span>
      </div>
      <div className="sc-columns">
        {context.columns.slice(0, 10).map((col, i) => (
          <span key={i} className="sc-col-tag" title={`数据类型: ${col.dataType}`}>
            {col.colLetter}: {col.colName}
          </span>
        ))}
      </div>
    </div>
  );
}
