import React, { useState, useRef } from "react";

interface Props {
  onSubmit: (request: string) => void;
  loading: boolean;
}

const EXAMPLES = [
  "计算薪资中位数的平均值",
  "统计一线岗位的数量",
  "查找薪资最高的岗位名称",
  "计算技术岗位薪资范围的平均值",
];

export default function ChatInput({ onSubmit, loading }: Props) {
  const [input, setInput] = useState("");
  const [showExamples, setShowExamples] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (text?: string) => {
    const req = (text || input).trim();
    if (!req || loading) return;
    onSubmit(req);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-input">
      <div className="input-row">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="描述你的计算需求，例如：计算所有一线岗位薪资中位数的平均值"
          disabled={loading}
        />
        <button
          className="btn-submit"
          onClick={() => handleSubmit()}
          disabled={loading || !input.trim()}
        >
          {loading ? "⏳" : "→"}
        </button>
      </div>

      <button
        className="btn-examples-toggle"
        onClick={() => setShowExamples(!showExamples)}
      >
        {showExamples ? "收起示例 ▲" : "查看示例 ▼"}
      </button>

      {showExamples && (
        <div className="examples">
          {EXAMPLES.map((ex, i) => (
            <button key={i} className="example-btn" onClick={() => handleSubmit(ex)}>
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
