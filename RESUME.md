# 简历项目描述（StudyOS）

> 说明：直接复制进简历的「项目经历」小节，按需删减。所有描述均与当前代码实现一致。
> 仓库：`github.com/<你的用户名>/studyos`（目前私有，建议 demo 录好后公开再放链接）。

## 项目经历：StudyOS · 个人 AI 学习工作台（简历项目）

**角色**：独立开发（全栈）　**技术栈**：Python / FastAPI / PostgreSQL(pgvector) / Redis / DeepSeek API / Sentence-Transformers / Next.js / Docker / MCP

**项目简介**：一个基于大模型的个人学习系统。用户上传学习资料后，系统自动解析分块、向量化建立个人知识库；基于知识库提供带来源引用的流式问答、自动出题与结构化批改、薄弱知识点记录，并用固定评测集量化检索质量。

**核心工作与成果**：

1. **实现 RAG 检索增强问答**：文档（Markdown/PDF/代码）上传后经 Redis 队列异步解析，标题感知分块并保留章节路径，用本地 BGE 向量模型（512 维）向量化存入 pgvector；提问时向量检索 top-K 片段，让模型只依据资料回答并标注 `[来源]`，相似度低于阈值时明确提示"证据不足"而非编造结论，有效控制幻觉。

2. **实现 SSE 流式问答**：后端以 `text/event-stream` 边生成边推送（先发来源 meta、再逐段推 delta），首 Token 延迟降低到几百毫秒，前端用 ReadableStream 逐段渲染。

3. **实现 Redis 队列与缓存**：文档解析（耗时数十秒）入队后由后台 worker（BRPOP）异步完成，上传接口秒级返回；相同问题在 TTL 内直接命中缓存，降低模型调用成本。

4. **实现结构化输出、Function Calling 与 MCP Server**：题目生成与批改通过 JSON Schema 约束模型输出（分维度打分、主要问题、建议复习点）；Agent 工具编排（`record_mistake` / `update_mastery` / `create_study_plan`）参数经 Pydantic 校验，状态变更持久化到 PostgreSQL 且可查询，设置最大步数与超时防失控；并将同一套工具用官方 `mcp` SDK 封装为标准 MCP Server（`tools/list` / `tools/call`，stdio 传输），任何支持 MCP 的客户端（如 Claude Code）可直接接入调用。

5. **搭建评测体系**：建立 20 题人工标注评测集，计算 Recall@K 与 MRR 量化召回质量，并评估引用正确性与完整性；记录每次模型调用的 token、延迟、估算成本，支撑成本观测。

6. **全栈交付**：FastAPI 后端（12 个接口）+ Next.js 前端（上传/问答/做题三页），Docker Compose 一键启动 PostgreSQL(pgvector)+Redis，端到端闭环（上传→问答→出题→批改→记薄弱点）跑通并录制约 2 分钟 demo。

## 面试可讲的一句话

"我独立完成了一个 RAG 学习助手：用 pgvector + 本地 embedding 建知识库，检索增强生成降低幻觉，SSE 流式降低首 Token 延迟，Redis 队列做异步解析、缓存省成本；同时把 Agent 工具封装成标准 MCP Server，理解了 Function Calling 是模型能力、MCP 是通信标准。"
