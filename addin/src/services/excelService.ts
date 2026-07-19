/// <reference types="@types/office-js" />
import type { SheetContext, ColumnInfo } from "../types";

// Excel 列号 → 列字母
function colLetter(idx: number): string {
  if (idx < 1) return "";
  if (idx <= 26) return String.fromCharCode(64 + idx);
  return colLetter(Math.floor((idx - 1) / 26)) + colLetter(((idx - 1) % 26) + 1);
}

// 检测列的数据类型
function detectColumnType(values: (string | number | boolean | undefined)[]): string {
  const nonNull = values.filter((v) => v !== null && v !== undefined && v !== "");
  if (nonNull.length === 0) return "empty";

  const allNum = nonNull.every((v) => typeof v === "number");
  if (allNum) return "numeric";

  const allStr = nonNull.every((v) => typeof v === "string");
  if (allStr) {
    const strVals = nonNull as string[];
    const rangeCount = strVals.filter((v) => /\d[\d,]*\s*[-~—]\s*\d[\d,]/.test(v)).length;
    if (rangeCount / strVals.length >= 0.3) return "text-range";

    const commaNumCount = strVals.filter((v) => /^\d{1,3}(,\d{3})*(\.\d+)?$/.test(v)).length;
    if (commaNumCount / strVals.length >= 0.5) return "numeric-with-comma";

    return "text";
  }

  return "mixed";
}

// 检测表头行
async function detectHeaderRow(): Promise<number> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getActiveWorksheet();
    const usedRange = sheet.getUsedRange(true);
    usedRange.load(["rowCount", "columnCount", "values"]);
    await context.sync();

    const maxRow = Math.min(usedRange.rowCount, 30);
    const maxCol = Math.min(usedRange.columnCount, 100);
    let bestRow = 1;
    let bestScore = -999;

    for (let r = 0; r < maxRow; r++) {
      let score = 0;
      let nonEmpty = 0;
      const rowValues = usedRange.values[r] || [];

      for (let c = 0; c < Math.min(rowValues.length, maxCol); c++) {
        const v = rowValues[c];
        if (v === null || v === undefined || v === "") continue;
        nonEmpty++;

        const s = String(v).trim();
        // 中文表头特征
        if (s.length >= 2 && s.length <= 30) score += 2;
        if (/[一-鿿]/.test(s)) score += 1;
        // 纯数字不像表头
        if (typeof v === "number") score -= 2;
      }

      if (nonEmpty > 0 && maxCol > 0) {
        const fillRatio = nonEmpty / Math.min(maxCol, nonEmpty + 5);
        if (fillRatio > 0.6) score += 3;
      }

      // 下一行有数字
      if (r + 1 < usedRange.rowCount) {
        const nextRow = usedRange.values[r + 1] || [];
        const numCount = nextRow.filter((v) => typeof v === "number").length;
        if (numCount >= 2) score += 5;
      }

      if (score > bestScore) {
        bestScore = score;
        bestRow = r + 1;
      }
    }

    return bestRow;
  });
}

// 提取工作表完整上下文
export async function getSheetContext(): Promise<SheetContext> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getActiveWorksheet();
    const usedRange = sheet.getUsedRange(true);
    usedRange.load(["rowCount", "columnCount", "values", "address"]);
    await context.sync();

    const headerRow = await detectHeaderRow();
    const firstDataRow = headerRow + 1;
    const lastDataRow = usedRange.rowCount;
    const colCount = usedRange.columnCount;

    const columns: ColumnInfo[] = [];

    for (let c = 0; c < colCount; c++) {
      const colIdx = c + 1;
      const headerVal = usedRange.values[headerRow - 1]?.[c];
      const colName = headerVal != null ? String(headerVal).trim() : colLetter(colIdx);

      const sampleValues: (string | number | boolean | undefined)[] = [];
      for (let r = headerRow; r < Math.min(usedRange.rowCount, headerRow + 10); r++) {
        sampleValues.push(usedRange.values[r]?.[c]);
      }

      columns.push({
        colLetter: colLetter(colIdx),
        colName,
        dataType: detectColumnType(sampleValues),
        sampleValues: sampleValues
          .filter((v) => v != null && v !== "")
          .slice(0, 3)
          .map((v) => String(v).substring(0, 30)),
      });
    }

    return {
      sheetName: sheet.name || "当前工作表",
      headerRow,
      firstDataRow,
      lastDataRow,
      columns,
      totalRows: lastDataRow - firstDataRow + 1,
    };
  });
}

// 获取当前选中的单元格地址
export async function getSelectedCell(): Promise<string> {
  return Excel.run(async (context) => {
    const range = context.workbook.getSelectedRange();
    range.load("address");
    await context.sync();
    return range.address.split("!").pop() || range.address;
  });
}

// 写入公式到选中的单元格
export async function writeFormulaToCell(formula: string): Promise<void> {
  return Excel.run(async (context) => {
    const range = context.workbook.getSelectedRange();
    range.formulas = [[formula]];
    await context.sync();
  });
}

// 读取选中区域的上下文（用于提示词构建）
export function buildContextPrompt(ctx: SheetContext): string {
  const lines: string[] = [
    `Sheet: ${ctx.sheetName}`,
    `表头行: 第${ctx.headerRow}行`,
    `数据行: ${ctx.firstDataRow}-${ctx.lastDataRow} (共${ctx.totalRows}行)`,
    `列:`,
  ];

  for (const col of ctx.columns) {
    const samples = col.sampleValues.length > 0 ? col.sampleValues.join(", ") : "无数据";
    lines.push(`  ${col.colLetter}(${col.colName}): ${col.dataType} | 示例: ${samples}`);
  }

  return lines.join("\n");
}

// Office.js 初始化
export async function initOffice(): Promise<void> {
  return new Promise((resolve, reject) => {
    Office.onReady((info) => {
      if (info.host === Office.HostType.Excel) {
        resolve();
      } else {
        reject(new Error("请在 Excel 中运行此插件"));
      }
    });
  });
}
