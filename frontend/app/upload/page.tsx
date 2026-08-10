"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

type Doc = {
  id: number;
  filename: string;
  file_type: string;
  parse_status: string;
};

export default function UploadPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);

  async function load() {
    const res = await fetch(`${API_BASE}/api/documents`);
    setDocs(await res.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function onUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/documents`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || "上传失败");
      }
      setFile(null);
      await load();
    } catch (e: any) {
      setError(e.message || "上传失败");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>StudyOS</h1>
        <nav>
          <Link href="/">首页</Link>
          <Link href="/qa">问答</Link>
          <Link href="/practice">做题</Link>
        </nav>
      </header>

      <div className="card">
        <h2>上传学习资料</h2>
        <p className="muted">支持 Markdown / TXT / PDF / 常见代码文件。解析在后台异步完成。</p>
        <div className="row" style={{ marginTop: 12 }}>
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button onClick={onUpload} disabled={!file || uploading}>
            {uploading ? "上传中..." : "上传"}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      <div className="card">
        <h2>已上传资料</h2>
        {docs.length === 0 ? (
          <p className="muted">还没有资料，先上传一份吧。</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>文件名</th>
                <th>类型</th>
                <th>解析状态</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.filename}</td>
                  <td>{d.file_type}</td>
                  <td>
                    <span className="badge">{d.parse_status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {docs.some((d) => d.parse_status !== "done") && (
          <p className="muted" style={{ marginTop: 8 }}>
            解析中会自动刷新，等状态变为 done 即可提问。
          </p>
        )}
      </div>
    </div>
  );
}
