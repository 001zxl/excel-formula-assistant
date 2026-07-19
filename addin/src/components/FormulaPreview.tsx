import React from "react";
import type { FormulaResult } from "../types";

interface Props {
  result: FormulaResult;
  onInsert: () => void;
}

const CONFIDENCE_LABELS: Record<string, { text: string; cls: string }> = {
  high: { text: "高", cls: "conf-high" },
  medium: { text: "中", cls: "conf-medium" },
  low: { text: "低", cls: "conf-low" },
};

export default function FormulaPreview({ result, onInsert }: Props) {
  const conf = CONFIDENCE_LABELS[result.confidence] || CONFIDENCE_LABELS.medium;

  return (
    <div className="formula-preview">
      {result.error ? (
        <div className="fp-error">{result.explanation_zh}</div>
      ) : (
        <>
          {/* 公式 + 插入按钮 */}
          <div className="fp-formula-row">
            <code className="fp-formula">{result.formula || "（无法生成）"}</code>
            <span className={`fp-confidence ${conf.cls}`}>置信度: {conf.text}</span>
          </div>

          {/* 解释 */}
          {result.explanation_zh && (
            <p className="fp-explanation">{result.explanation_zh}</p>
          )}

          {/* 插入按钮 */}
          {result.formula && (
            <button className="btn-insert" onClick={onInsert}>
              📌 插入到当前单元格
            </button>
          )}

          {/* 备选方案 */}
          {result.alternative_formulas.length > 0 && (
            <div className="fp-alt">
              <strong>备选方案:</strong>
              {result.alternative_formulas.map((f, i) => (
                <code key={i}>{f}</code>
              ))}
            </div>
          )}

          {/* 警告 */}
          {result.warnings.length > 0 && (
            <div className="fp-warnings">
              {result.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}

          {/* 前提 */}
          {result.dependencies.length > 0 && (
            <div className="fp-deps">
              <strong>使用前提:</strong>
              {result.dependencies.map((d, i) => (
                <div key={i}>- {d}</div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
