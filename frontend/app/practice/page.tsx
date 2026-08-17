"use client";

import { useState } from "react";
import { AppShell } from "@/app/components/app-shell";
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

const topicSuggestions = ["RAG 检索", "Function Calling", "Embedding", "Agent 安全边界"];

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

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
      const response = await fetch(`${API_BASE}/api/practice/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "出题失败");
      setQuestion(data);
    } catch (generateError) {
      setError(errorMessage(generateError, "出题失败"));
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit() {
    if (!question || !answer.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/practice/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: question.id, answer }),
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "批改失败");
      setGrade(data);
    } catch (submitError) {
      setError(errorMessage(submitError, "批改失败"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell
      eyebrow="Practice deliberately"
      title="用练习确认真正掌握的部分"
      description="从知识库中选择一个主题生成题目。回答后会按维度批改，并整理下一步需要复习的内容。"
    >
      <section className="card">
        <div className="section-heading">
          <div>
            <h2>选择练习主题</h2>
            <p>建议一次只练一个明确概念。</p>
          </div>
        </div>
        <label className="field-label" htmlFor="topic">主题</label>
        <input
          id="topic"
          type="text"
          placeholder="例如：RAG 中的召回与排序"
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") onGenerate();
          }}
        />
        <div className="suggestions">
          {topicSuggestions.map((suggestion) => (
            <button className="suggestion" key={suggestion} onClick={() => setTopic(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
        <div className="button-row">
          <button onClick={onGenerate} disabled={loading || !topic.trim()}>
            {loading && !question ? "正在准备" : "生成题目"}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </section>

      {question ? (
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>练习题</h2>
              <p>先独立作答，再查看结构化反馈。</p>
            </div>
            <div className="tag-row">
              <span className="badge neutral">{question.question_type}</span>
              <span className="badge neutral">{question.difficulty}</span>
            </div>
          </div>
          <div className="question-content">{question.content}</div>
          {question.options && (
            <ul className="option-list">
              {question.options.map((option) => <li key={option}>{option}</li>)}
            </ul>
          )}
          {question.knowledge_points.length > 0 && (
            <div className="tag-row">
              {question.knowledge_points.map((point) => <span className="badge" key={point}>{point}</span>)}
            </div>
          )}
          <label className="field-label" htmlFor="answer">你的答案</label>
          <textarea
            id="answer"
            rows={5}
            placeholder="写下你的理解、推理过程或关键步骤"
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
          />
          <div className="button-row">
            <button onClick={onSubmit} disabled={loading || !answer.trim()}>
              {loading ? "正在批改" : "提交答案"}
            </button>
            <button className="secondary" onClick={onGenerate} disabled={loading}>换一道题</button>
          </div>
        </section>
      ) : (
        <section className="empty-state">
          <div><strong>还没有生成题目</strong><span>选择主题后，题目会基于你的知识库内容生成。</span></div>
        </section>
      )}

      {grade && (
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>批改结果</h2>
              <p>{grade.feedback}</p>
            </div>
            <span className={`badge ${grade.passed ? "" : "danger"}`}>
              {grade.passed ? "已通过" : "继续复习"}
            </span>
          </div>
          <div className="score-block">
            <strong>{grade.score}</strong><span className="muted">分</span>
          </div>
          <div className="result-grid">
            {grade.dimensions.map((dimension) => (
              <div className="result-item" key={dimension.name}>
                <strong>{dimension.name} · {dimension.score}</strong>
                <p>{dimension.comment}</p>
              </div>
            ))}
          </div>
          {grade.mistakes.length > 0 && (
            <div>
              <span className="field-label">需要继续复习</span>
              <div className="tag-row">
                {grade.mistakes.map((mistake) => <span className="badge danger" key={mistake}>{mistake}</span>)}
              </div>
            </div>
          )}
          {grade.suggested_review.length > 0 && (
            <div className="notice">建议：{grade.suggested_review.join("；")}</div>
          )}
        </section>
      )}
    </AppShell>
  );
}
