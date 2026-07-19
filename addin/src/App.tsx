import React, { useState, useEffect, useCallback } from "react";
import { initOffice, getSheetContext, getSelectedCell, writeFormulaToCell } from "./services/excelService";
import { generateFormula, checkProxyHealth, loadHistory, saveHistory } from "./services/aiService";
import ChatInput from "./components/ChatInput";
import FormulaPreview from "./components/FormulaPreview";
import SheetContextPanel from "./components/SheetContextPanel";
import HistoryPanel from "./components/HistoryPanel";
import type { SheetContext, FormulaResult, HistoryEntry } from "./types";

type Tab = "generate" | "history" | "settings";

export default function App() {
  const [ready, setReady] = useState(false);
  const [proxyOk, setProxyOk] = useState(false);
  const [tab, setTab] = useState<Tab>("generate");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FormulaResult | null>(null);
  const [sheetCtx, setSheetCtx] = useState<SheetContext | null>(null);
  const [selectedCell, setSelectedCell] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState("");
  const [insertStatus, setInsertStatus] = useState("");

  // 初始化
  useEffect(() => {
    initOffice()
      .then(() => setReady(true))
      .catch((e) => setError("请在 Excel 中打开此插件: " + e.message));

    checkProxyHealth().then(setProxyOk);
    setHistory(loadHistory());
  }, []);

  // 刷新工作表上下文
  const refreshContext = useCallback(async () => {
    try {
      const ctx = await getSheetContext();
      setSheetCtx(ctx);
      const cell = await getSelectedCell();
      setSelectedCell(cell);
    } catch (e: any) {
      setError("读取工作表失败: " + e.message);
    }
  }, []);

  useEffect(() => {
    if (ready) refreshContext();
  }, [ready, refreshContext]);

  // 生成公式
  const handleGenerate = useCallback(
    async (request: string) => {
      if (!sheetCtx) {
        setError("请先打开一个 Excel 工作表");
        return;
      }
      setLoading(true);
      setError("");
      setResult(null);
      setInsertStatus("");

      try {
        const res = await generateFormula(request, sheetCtx);
        setResult(res);
        // 保存历史
        const entry: HistoryEntry = {
          id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
          timestamp: Date.now(),
          sheetName: sheetCtx.sheetName,
          request,
          formula: res.formula,
          explanation_zh: res.explanation_zh,
          cellAddress: selectedCell,
        };
        saveHistory(entry);
        setHistory(loadHistory());
      } catch (e: any) {
        setError("生成失败: " + e.message);
      } finally {
        setLoading(false);
      }
    },
    [sheetCtx, selectedCell]
  );

  // 插入公式到单元格
  const handleInsert = useCallback(async () => {
    if (!result?.formula) return;
    try {
      await writeFormulaToCell(result.formula);
      setInsertStatus(`✅ 已写入 ${selectedCell || "当前单元格"}`);
      setTimeout(() => setInsertStatus(""), 3000);
    } catch (e: any) {
      setInsertStatus(`❌ 写入失败: ${e.message}`);
    }
  }, [result, selectedCell]);

  // 选择历史记录
  const handleSelectHistory = (entry: HistoryEntry) => {
    setResult({
      formula: entry.formula,
      explanation_zh: entry.explanation_zh,
      confidence: "high",
      alternative_formulas: [],
      warnings: [],
      dependencies: [],
      error: false,
    });
    setTab("generate");
  };

  if (!ready) {
    return (
      <div className="app-loading">
        <p>正在加载 Excel 公式助手...</p>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="app">
      {/* 顶部状态栏 */}
      <div className="status-bar">
        <span className={`status-dot ${proxyOk ? "ok" : "err"}`} />
        <span>{proxyOk ? "AI 就绪" : "代理未连接"}</span>
        {sheetCtx && (
          <span className="status-info">
            {sheetCtx.sheetName} · {selectedCell || "未选中"}
          </span>
        )}
        <button className="btn-refresh" onClick={refreshContext} title="刷新工作表信息">
          ↻
        </button>
      </div>

      {/* 标签切换 */}
      <div className="tabs">
        <button className={`tab ${tab === "generate" ? "active" : ""}`} onClick={() => setTab("generate")}>
          生成公式
        </button>
        <button className={`tab ${tab === "history" ? "active" : ""}`} onClick={() => setTab("history")}>
          历史记录
        </button>
        <button className={`tab ${tab === "settings" ? "active" : ""}`} onClick={() => setTab("settings")}>
          设置
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError("")}>✕</button>
        </div>
      )}

      {/* 标签内容 */}
      {tab === "generate" && (
        <div className="tab-content">
          <SheetContextPanel context={sheetCtx} />
          <ChatInput onSubmit={handleGenerate} loading={loading} />
          {loading && <div className="loading">AI 正在生成公式...</div>}
          {insertStatus && <div className="insert-status">{insertStatus}</div>}
          {result && <FormulaPreview result={result} onInsert={handleInsert} />}
        </div>
      )}

      {tab === "history" && <HistoryPanel history={history} onSelect={handleSelectHistory} />}

      {tab === "settings" && (
        <div className="tab-content settings">
          <h3>设置</h3>
          <div className="setting-item">
            <label>代理服务器</label>
            <input type="text" value="http://localhost:8100" readOnly />
          </div>
          <div className="setting-item">
            <label>模型</label>
            <input type="text" value="deepseek-v4-pro" readOnly />
          </div>
          <p className="hint">API Key 和模型配置在本地代理服务器中管理，不会暴露在插件中。</p>
        </div>
      )}
    </div>
  );
}
