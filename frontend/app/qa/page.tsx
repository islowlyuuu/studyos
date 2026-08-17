"use client";

import { useRef, useState } from "react";
import { AppShell } from "@/app/components/app-shell";
import { API_BASE, readSSE } from "@/lib/api";

type Source = {
  index: number;
  filename: string;
  heading_path: string;
  page_number: number | null;
};

const suggestions = [
  "RAG 为什么能减少幻觉？",
  "解释 Function Calling 的执行过程",
  "Recall@K 和 MRR 有什么区别？",
];

export default function QAPage() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [cached, setCached] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function onAsk() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError("");
    setAnswer("");
    setSources([]);
    setCached(false);
    abortRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE}/api/qa/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: abortRef.current.signal,
      });
      if (!response.ok || !response.body) throw new Error("请求失败，请确认后端已启动");

      await readSSE(response.body.getReader(), (event) => {
        if (event.type === "meta") {
          setSources(event.sources ?? []);
          setCached(event.cached ?? false);
        } else if (event.type === "delta") {
          setAnswer((current) => current + event.text);
        }
      });
    } catch (requestError) {
      if (requestError instanceof Error && requestError.name !== "AbortError") {
        setError(requestError.message || "请求失败");
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function onStop() {
    abortRef.current?.abort();
    setLoading(false);
  }

  return (
    <AppShell
      eyebrow="Ask with evidence"
      title="从自己的资料里找答案"
      description="回答只使用知识库中的内容，并附上可以回到原文核对的来源。资料不足时，系统会直接说明。"
    >
      <section className="card">
        <div className="section-heading">
          <div>
            <h2>输入问题</h2>
            <p>问题越具体，检索到的片段通常越准确。</p>
          </div>
          <span className="badge neutral">流式回答</span>
        </div>
        <label className="field-label" htmlFor="question">你的问题</label>
        <textarea
          id="question"
          rows={4}
          placeholder="例如：标题感知分块相比固定长度切分有什么优势？"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") onAsk();
          }}
        />
        <div className="suggestions" aria-label="示例问题">
          {suggestions.map((suggestion) => (
            <button className="suggestion" key={suggestion} onClick={() => setQuery(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
        <div className="button-row">
          <button onClick={onAsk} disabled={loading || !query.trim()}>
            {loading ? "正在查找" : "开始提问"}
          </button>
          {loading && <button className="secondary" onClick={onStop}>停止生成</button>}
          <span className="muted">⌘ / Ctrl + Enter 提交</span>
        </div>
        {error && <div className="error">{error}</div>}
      </section>

      {answer ? (
        <section className="card answer-card">
          <div className="answer-header">
            <h2>回答</h2>
            <div className="tag-row">
              {cached && <span className="badge neutral">缓存结果</span>}
              {loading && <span className="status-badge neutral">生成中</span>}
            </div>
          </div>
          <div className={`answer${loading ? " blink" : ""}`}>{answer}</div>
          {sources.length > 0 && (
            <div className="sources">
              <h3>引用来源</h3>
              {sources.map((source) => (
                <span className="source-item" key={source.index}>
                  [{source.index}] {source.filename}
                  {source.heading_path ? ` · ${source.heading_path}` : ""}
                  {source.page_number ? ` · 第 ${source.page_number} 页` : ""}
                </span>
              ))}
            </div>
          )}
        </section>
      ) : (
        <section className="empty-state">
          <div>
            <strong>答案会显示在这里</strong>
            <span>系统会先检索资料，再逐步返回回答和引用。</span>
          </div>
        </section>
      )}
    </AppShell>
  );
}
