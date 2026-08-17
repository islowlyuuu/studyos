"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/app/components/app-shell";
import { API_BASE } from "@/lib/api";

type Doc = {
  id: number;
  filename: string;
  file_type: string;
  parse_status: string;
  version: number;
  is_active: boolean;
  content_hash: string;
  embedding_model: string;
  indexed_at: string | null;
};

const statusText: Record<string, string> = {
  pending: "等待处理",
  parsing: "正在解析",
  done: "可用",
  failed: "处理失败",
  cancelled: "已取消",
  deleted: "已删除",
};

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function UploadPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [serviceError, setServiceError] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [file, setFile] = useState<File | null>(null);

  async function load(silent = false) {
    try {
      const response = await fetch(`${API_BASE}/api/documents`);
      if (!response.ok) throw new Error("资料服务暂时不可用");
      setDocs(await response.json());
      setServiceError("");
    } catch {
      if (!silent) setServiceError("后端服务尚未连接，启动后这里会显示已导入资料。");
    }
  }

  useEffect(() => {
    load();
    const timer = window.setInterval(() => load(true), 4000);
    return () => window.clearInterval(timer);
  }, []);

  async function send(fileToSend: File, replaceId?: number) {
    const form = new FormData();
    form.append("file", fileToSend);
    const path = replaceId ? `/api/documents/${replaceId}/replace` : "/api/documents";
    const response = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "上传失败");
    setNotice(
      body.duplicate
        ? `资料已存在：${body.document.filename}`
        : `${body.document.filename} 已进入解析队列`,
    );
  }

  async function onUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    setNotice("");
    try {
      await send(file);
      setFile(null);
      await load();
    } catch (uploadError) {
      setError(errorMessage(uploadError, "上传失败"));
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(id: number) {
    if (!confirm("删除后该资料不会再参与检索，确定继续？")) return;
    try {
      const response = await fetch(`${API_BASE}/api/documents/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("删除失败");
      await load();
    } catch (deleteError) {
      setError(errorMessage(deleteError, "删除失败"));
    }
  }

  async function onReplace(id: number, selected: File | null) {
    if (!selected) return;
    setUploading(true);
    setError("");
    try {
      await send(selected, id);
      await load();
    } catch (replaceError) {
      setError(errorMessage(replaceError, "替换失败"));
    } finally {
      setUploading(false);
    }
  }

  return (
    <AppShell
      eyebrow="Knowledge library"
      title="整理你的学习资料"
      description="导入笔记、PDF 或代码文档。系统会在后台解析并建立索引，相同内容不会重复入库。"
    >
      <div className="two-column">
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>添加资料</h2>
              <p>支持 Markdown、TXT、PDF 与常见代码文件。</p>
            </div>
          </div>
          <div className="upload-zone">
            <div>
              <span className="upload-zone-icon" aria-hidden="true">↑</span>
              <strong>{file ? "文件已选择" : "选择一份学习资料"}</strong>
              <p>{file ? "确认后会进入后台解析队列" : "单个文件上传，方便保留清晰来源"}</p>
              <label className="file-button">
                {file ? "重新选择" : "浏览文件"}
                <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              </label>
              {file && <div className="selected-file">{file.name}</div>}
            </div>
          </div>
          <div className="button-row">
            <button onClick={onUpload} disabled={!file || uploading}>
              {uploading ? "正在提交" : "开始处理"}
            </button>
          </div>
          {error && <div className="error">{error}</div>}
          {notice && <div className="notice">{notice}</div>}
        </section>

        <aside className="panel">
          <div className="section-heading">
            <div>
              <h2>资料建议</h2>
              <p>先小而精，再逐步增加。</p>
            </div>
          </div>
          <div className="result-grid">
            <div className="result-item">
              <strong>保留标题</strong>
              <p>清晰章节能改善切分与引用定位。</p>
            </div>
            <div className="result-item">
              <strong>避免重复</strong>
              <p>相同内容会自动识别，不重复建立向量。</p>
            </div>
            <div className="result-item">
              <strong>及时替换</strong>
              <p>资料更新时上传新版本，旧版会退出检索。</p>
            </div>
            <div className="result-item">
              <strong>从真实问题出发</strong>
              <p>优先导入你确实会查阅和复习的内容。</p>
            </div>
          </div>
        </aside>
      </div>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>资料库</h2>
            <p>{docs.length > 0 ? `当前共 ${docs.length} 个索引版本` : "查看解析状态与活动版本"}</p>
          </div>
          {docs.some((doc) => doc.parse_status === "pending" || doc.parse_status === "parsing") && (
            <span className="status-badge neutral">处理中</span>
          )}
        </div>

        {serviceError ? (
          <div className="empty-state">
            <div><strong>资料服务未连接</strong><span>{serviceError}</span></div>
          </div>
        ) : docs.length === 0 ? (
          <div className="empty-state">
            <div><strong>资料库还是空的</strong><span>上传第一份资料后，索引状态会显示在这里。</span></div>
          </div>
        ) : (
          <div className="document-list">
            <div className="document-row document-head">
              <span>资料</span><span>版本</span><span>状态</span><span>索引时间</span><span>操作</span>
            </div>
            {docs.map((doc) => (
              <div className="document-row" key={doc.id}>
                <div className="document-name">
                  <strong>{doc.filename}</strong>
                  <small>{doc.file_type.toUpperCase()}{doc.is_active ? " · 活动版本" : ""}</small>
                </div>
                <span className="muted">v{doc.version}</span>
                <span className={`status-badge ${doc.parse_status === "done" ? "" : "neutral"}`}>
                  {statusText[doc.parse_status] || doc.parse_status}
                </span>
                <span className="muted">
                  {doc.indexed_at ? new Date(doc.indexed_at).toLocaleString("zh-CN") : "—"}
                </span>
                <div className="document-actions">
                  <label className="replace-label">
                    替换
                    <input
                      aria-label={`替换 ${doc.filename}`}
                      type="file"
                      onChange={(event) => onReplace(doc.id, event.target.files?.[0] ?? null)}
                      disabled={uploading}
                    />
                  </label>
                  <button className="compact danger" onClick={() => onDelete(doc.id)} disabled={uploading}>
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
