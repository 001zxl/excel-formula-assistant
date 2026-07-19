import type { FormulaResult, SheetContext } from "../types";
import { buildContextPrompt } from "./excelService";

// 代理地址：打包模式用当前 origin（与服务器同端口），开发模式用 localhost:8100
const PROXY_URL =
  window.location.port === "3000"
    ? "https://localhost:8100"
    : window.location.origin;

// 调用后端生成公式
export async function generateFormula(
  userRequest: string,
  sheetContext: SheetContext,
): Promise<FormulaResult> {
  const contextPrompt = buildContextPrompt(sheetContext);

  const response = await fetch(`${PROXY_URL}/api/generate-formula`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request: userRequest,
      sheet_context: contextPrompt,
      sheet_name: sheetContext.sheetName,
      header_row: sheetContext.headerRow,
      first_data_row: sheetContext.firstDataRow,
      last_data_row: sheetContext.lastDataRow,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    return {
      formula: "",
      explanation_zh: `请求失败（${response.status}）: ${errText}`,
      confidence: "low",
      alternative_formulas: [],
      warnings: [],
      dependencies: [],
      error: true,
    };
  }

  return response.json();
}

// 检查代理是否可用
export async function checkProxyHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${PROXY_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// 历史记录存储（localStorage）
export function loadHistory(): import("../types").HistoryEntry[] {
  try {
    const raw = localStorage.getItem("excel-formula-history");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveHistory(entry: import("../types").HistoryEntry): void {
  const history = loadHistory();
  history.unshift(entry);
  // 保留最近 50 条
  if (history.length > 50) history.splice(50);
  localStorage.setItem("excel-formula-history", JSON.stringify(history));
}

export function clearHistory(): void {
  localStorage.removeItem("excel-formula-history");
}
