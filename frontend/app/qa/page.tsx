"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { API_BASE, readSSE } from "@/lib/api";

type Source = {
  index: number;
  filename: string;
  heading_path: string;
  page_number: number | null;
};

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
      const res = await fetch(`${API_BASE}/api/qa/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: abortRef.current.signal,
      });
      if (!res.ok || !res.body) throw new Error("请求失败，请确认后端已启动");

      const reader = res.body.getReader();
      await readSSE(reader, (ev) => {
        if (ev.type === "meta") {
          setSources(ev.sources ?? []);
          setCached(ev.cached ?? false);
        } else if (ev.type === "delta") {
          setAnswer((prev) => prev + ev.text);
        }
      });
    } catch (e: any) {
      if (e.name !== "AbortError") setError(e.message || "请求失败");
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
    <div className="container">
      <header>
        <h1>StudyOS</h1>
        <nav>
          <Link href="/">首页</Link>
          <Link href="/upload">上传资料</Link>
          <Link href="/practice">做题</Link>
        </nav>
      </header>

      <div className="card">
        <h2>基于知识库问答（SSE 流式）</h2>
        <textarea
          rows={3}
          placeholder="输入你的问题，例如：什么是 RAG？"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="row">
          <button onClick={onAsk} disabled={loading || !query.trim()}>
            {loading ? "生成中..." : "提问"}
          </button>
          {loading && <button onClick={onStop}>停止</button>}
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {answer && (
        <div className="card">
          <h2>
            回答 {cached && <span className="badge">命中缓存</span>}
          </h2>
          <div className={`answer${loading ? " blink" : ""}`}>{answer}</div>
          {sources.length > 0 && (
            <div className="sources">
              <strong>来源：</strong>
              {sources.map((s) => (
                <span className="badge" key={s.index}>
                  [{s.index}] {s.filename}
                  {s.heading_path ? ` · ${s.heading_path}` : ""}
                  {s.page_number ? ` · 第${s.page_number}页` : ""}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
