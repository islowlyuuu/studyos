import Link from "next/link";

export default function Home() {
  return (
    <div className="container">
      <header>
        <h1>StudyOS</h1>
        <nav>
          <Link href="/upload">上传资料</Link>
          <Link href="/qa">问答</Link>
          <Link href="/practice">做题</Link>
        </nav>
      </header>
      <div className="card">
        <h2>个人 AI 学习工作台</h2>
        <p className="muted">
          上传学习资料 → 建立个人知识库 → 带来源引用的问答（SSE 流式）→ 自动出题 → 结构化批改 → 记录薄弱知识点。
        </p>
        <div style={{ marginTop: 12 }}>
          <Link href="/upload">1. 上传资料</Link> →{" "}
          <Link href="/qa">2. 提问</Link> →{" "}
          <Link href="/practice">3. 做题</Link>
        </div>
      </div>
    </div>
  );
}
