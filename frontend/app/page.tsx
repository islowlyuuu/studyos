import Link from "next/link";
import { AppShell } from "@/app/components/app-shell";

const actions = [
  {
    step: "01",
    title: "整理资料",
    description: "导入笔记、PDF 与项目文档，保留清晰的版本和来源。",
    href: "/upload",
  },
  {
    step: "02",
    title: "带着出处提问",
    description: "回答基于你的资料生成，关键结论可以回到原文核对。",
    href: "/qa",
  },
  {
    step: "03",
    title: "用练习巩固",
    description: "围绕知识库生成题目，记录反馈与需要继续复习的内容。",
    href: "/practice",
  },
];

export default function Home() {
  return (
    <AppShell>
      <section className="hero">
        <div>
          <p className="eyebrow">Your learning workspace</p>
          <h1>把零散资料，慢慢变成自己的知识体系。</h1>
          <p className="hero-copy">
            StudyOS 帮你整理学习材料、核对答案出处，再通过练习发现真正没有掌握的部分。
          </p>
          <div className="hero-actions">
            <Link className="button-link" href="/upload">
              开始整理资料
            </Link>
            <Link className="button-link secondary" href="/qa">
              进入问答
            </Link>
          </div>
        </div>
        <aside className="hero-note">
          <span>今日建议</span>
          <strong>先建立一组可信资料，再开始提问。</strong>
          <p>来源越清晰，回答和练习越容易验证。</p>
        </aside>
      </section>

      <section className="home-grid" aria-label="学习流程">
        {actions.map((action) => (
          <Link className="action-card" href={action.href} key={action.step}>
            <div>
              <span className="step">{action.step}</span>
              <h2>{action.title}</h2>
              <p>{action.description}</p>
            </div>
            <span className="arrow" aria-hidden="true">→</span>
          </Link>
        ))}
      </section>
    </AppShell>
  );
}
