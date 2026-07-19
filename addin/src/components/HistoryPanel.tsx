import React from "react";
import type { HistoryEntry } from "../types";
import { clearHistory } from "../services/aiService";

interface Props {
  history: HistoryEntry[];
  onSelect: (entry: HistoryEntry) => void;
}

export default function HistoryPanel({ history, onSelect }: Props) {
  if (history.length === 0) {
    return (
      <div className="tab-content history-empty">
        <p>暂无历史记录</p>
        <p className="hint">生成的公式会自动保存在这里</p>
      </div>
    );
  }

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  };

  return (
    <div className="tab-content history">
      <div className="history-header">
        <span>共 {history.length} 条记录</span>
        <button
          className="btn-clear"
          onClick={() => {
            if (confirm("确定清空所有历史记录？")) {
              clearHistory();
              window.location.reload();
            }
          }}
        >
          清空
        </button>
      </div>
      {history.map((entry) => (
        <div key={entry.id} className="history-item" onClick={() => onSelect(entry)}>
          <div className="hi-header">
            <span className="hi-time">{formatDate(entry.timestamp)}</span>
            <span className="hi-sheet">{entry.sheetName}</span>
          </div>
          <div className="hi-request">"{entry.request}"</div>
          <code className="hi-formula">{entry.formula}</code>
        </div>
      ))}
    </div>
  );
}
