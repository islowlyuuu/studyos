"use client";

import Link from "next/link";
import { useState } from "react";
import { API_BASE } from "@/lib/api";

type Question = {
  id: number;
  question_type: string;
  difficulty: string;
  content: string;
  options: string[] | null;
  knowledge_points: string[];
};

type Grade = {
  attempt_id: number;
  score: number;
  dimensions: { name: string; score: number; comment: string }[];
  feedback: string;
  mistakes: string[];
  suggested_review: string[];
  passed: boolean;
};

export default function PracticePage() {
  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState("");
  const [grade, setGrade] = useState<Grade | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onGenerate() {
    if (!topic.trim()) return;
    setLoading(true);
    setError("");
    setQuestion(null);
    setAnswer("");
    setGrade(null);
    try {
      const res = await fetch(`${API_BASE}/api/practice/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "出题失败");
      setQuestion(data);
    } catch (e: any) {
      setError(e.message || "出题失败");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit() {
    if (!question || !answer.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/practice/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: question.id, answer }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "批改失败");
      setGrade(data);
    } catch (e: any) {
      setError(e.message || "批改失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>StudyOS</h1>
        <nav>
          <Link href="/">首页</Link>
          <Link href="/upload">上传资料</Link>
          <Link href="/qa">问答</Link>
        </nav>
      </header>

      <div className="card">
        <h2>基于知识库出题</h2>
        <input
          type="text"
          placeholder="输入想练的主题，例如：RAG 检索"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button onClick={onGenerate} disabled={loading || !topic.trim()}>
          {loading ? "生成中..." : "生成题目"}
        </button>
        {error && <div className="error">{error}</div>}
      </div>

      {question && (
        <div className="card">
          <h2>
            题目{" "}
            <span className="badge">{question.question_type}</span>
            <span className="badge">{question.difficulty}</span>
          </h2>
          <p>{question.content}</p>
          {question.options && (
            <ul style={{ margin: "10px 0 0 18px" }}>
              {question.options.map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          )}
          {question.knowledge_points.length > 0 && (
            <p className="muted" style={{ marginTop: 8 }}>
              考察知识点：
              {question.knowledge_points.map((kp) => (
                <span className="badge" key={kp}>
                  {kp}
                </span>
              ))}
            </p>
          )}

          <textarea
            rows={4}
            placeholder="输入你的答案"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            style={{ marginTop: 12 }}
          />
          <button onClick={onSubmit} disabled={loading || !answer.trim()}>
            {loading ? "批改中..." : "提交批改"}
          </button>
        </div>
      )}

      {grade && (
        <div className="card">
          <h2>
            批改结果{" "}
            <span className="badge" style={grade.passed ? { background: "#e6f7ee", color: "#1d9d5f" } : { background: "#fdeeee", color: "#d64545" }}>
              {grade.passed ? "通过" : "未通过"} · {grade.score} 分
            </span>
          </h2>
          <table>
            <thead>
              <tr>
                <th>维度</th>
                <th>得分</th>
                <th>点评</th>
              </tr>
            </thead>
            <tbody>
              {grade.dimensions.map((d, i) => (
                <tr key={i}>
                  <td>{d.name}</td>
                  <td>{d.score}</td>
                  <td>{d.comment}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: 12 }}>{grade.feedback}</p>
          {grade.mistakes.length > 0 && (
            <p className="muted" style={{ marginTop: 8 }}>
              薄弱知识点：
              {grade.mistakes.map((m) => (
                <span className="badge" key={m}>
                  {m}
                </span>
              ))}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
