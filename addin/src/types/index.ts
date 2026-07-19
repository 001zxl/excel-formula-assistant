/// <reference types="@types/office-js" />

// Excel 公式助手 — 类型定义

// 工作表上下文（镜像 Python 的 SheetContext）
export interface ColumnInfo {
  colLetter: string;
  colName: string;
  dataType: string;
  sampleValues: string[];
}

export interface SheetContext {
  sheetName: string;
  headerRow: number;
  firstDataRow: number;
  lastDataRow: number;
  columns: ColumnInfo[];
  totalRows: number;
}

// AI 公式结果（镜像 Python 的 FormulaResult）
export interface FormulaResult {
  formula: string;
  explanation_zh: string;
  confidence: "high" | "medium" | "low";
  alternative_formulas: string[];
  warnings: string[];
  dependencies: string[];
  error: boolean;
}

// 历史记录
export interface HistoryEntry {
  id: string;
  timestamp: number;
  sheetName: string;
  request: string;
  formula: string;
  explanation_zh: string;
  cellAddress: string;
}

// 插件状态
export type TabId = "generate" | "history" | "settings";

export interface AppState {
  activeTab: TabId;
  isLoading: boolean;
  result: FormulaResult | null;
  sheetContext: SheetContext | null;
  selectedCell: string;
  history: HistoryEntry[];
}
