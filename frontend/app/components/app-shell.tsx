"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navigation = [
  { href: "/", label: "概览" },
  { href: "/upload", label: "资料" },
  { href: "/qa", label: "问答" },
  { href: "/practice", label: "练习" },
];

type AppShellProps = {
  children: ReactNode;
  eyebrow?: string;
  title?: string;
  description?: string;
};

export function AppShell({ children, eyebrow, title, description }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="app-frame">
      <header className="site-header">
        <Link className="brand" href="/" aria-label="StudyOS 首页">
          <span className="brand-mark">S</span>
          <span>
            <strong>StudyOS</strong>
            <small>个人学习工作台</small>
          </span>
        </Link>
        <nav className="site-nav" aria-label="主要导航">
          {navigation.map((item) => (
            <Link
              className={pathname === item.href ? "active" : undefined}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="page-shell">
        {title && (
          <section className="page-heading">
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <h1>{title}</h1>
            {description && <p>{description}</p>}
          </section>
        )}
        {children}
      </main>
      <footer className="site-footer">本地知识，按你的节奏积累。</footer>
    </div>
  );
}
