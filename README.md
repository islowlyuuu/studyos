# StudyOS · 个人 AI 学习工作台

上传学习资料，建立个人可检索知识库；基于知识库做带来源引用的问答（SSE 流式）、自动出题、结构化批改、记录薄弱知识点，并支持 Agent 工具调用（记录错题 / 更新掌握度 / 生成学习计划）。配套固定评测集量化 RAG 召回质量。

一个用于学习 RAG / 结构化输出 / Function Calling / LLM 评测的端到端简历项目。

## 架构

```
┌─────────────────────────────┐
│  frontend (Next.js)         │
│  /upload  /qa  /practice    │
│  问答走 SSE 流式 (fetch +    │
│  ReadableStream)            │
└──────────────┬──────────────┘
               │ HTTP / SSE
┌──────────────▼──────────────┐
│  backend (FastAPI)          │
│  /api/documents  /api/qa    │
│  /api/practice  /api/agent  │
└───────┬──────────┬──────────┘
        │          │
   ┌────▼────┐  ┌──▼──────────────┐
   │PostgreSQL│ │ Redis           │
   │ +pgvector│ │ 队列: 文档解析   │
   │ 状态+向量 │ │ 缓存: LLM 响应  │
   └─────────┘  └────────┬────────┘
                         │ BRPOP
                   ┌─────▼─────┐
                   │ worker    │ 解析→分块→embedding→入库
                   └───────────┘
        DeepSeek (chat, 流式, Function Calling)
        BGE 本地向量模型 (sentence-transformers, 512 维)
```

## 技术栈

- **后端**：FastAPI + SQLAlchemy + PostgreSQL（pgvector 向量检索）
- **队列/缓存**：Redis（文档解析后台任务 + LLM 响应缓存 TTL）
- **Chat 模型**：DeepSeek（OpenAI 兼容接口；流式、JSON 结构化输出、Function Calling）
- **Embedding**：本地 BGE 小模型（`BAAI/bge-small-zh-v1.5`，512 维，免费离线）
- **前端**：Next.js（最小版：上传 / 问答 / 做题）

## 核心能力

| 模块 | 说明 |
|------|------|
| 知识库 (RAG) | 文档上传（md/txt/pdf/代码）→ 标题感知分块 → 向量化入库 → 向量检索 → 带引用问答；证据不足时明确说明，不编造 |
| 流式输出 | 问答走 SSE（`text/event-stream`），首 Token 低延迟，前端逐段渲染 |
| 缓存 | 相同问题在 TTL 内直接命中 Redis，降低模型调用成本 |
| 练习与批改 | 基于知识库自动出题（JSON Schema 结构化输出）→ 提交答案 → 分维度打分 + 薄弱知识点标记 |
| Agent | Function Calling 工具编排（`record_mistake` / `update_mastery` / `create_study_plan`），参数 Pydantic 校验，状态持久化到 PG，最大步数 + 超时保护 |
| MCP Server | 把同一套 Agent 工具暴露为标准 MCP 协议（`tools/list` / `tools/call`），任何支持 MCP 的客户端（如 Claude Code）可直接调用 |
| 评测 | 固定 20 题评测集，计算 Recall@K / MRR / 引用正确率 / 完整性；每次模型调用记录 token、延迟、估算成本 |

## 快速开始

### 0. 前置

- Windows 上装 Docker（PostgreSQL+pgvector、Redis 跑在 Docker/WSL 里）
- Python 3.11+，Node 18+

### 1. 启动数据库与 Redis

```bash
cd studyos
docker compose up -d
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows；Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env          # 填入 DEEPSEEK_API_KEY
# 如首次建库表结构有变化：python migrate.py

# 两个终端，分别跑：
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # API
.venv\Scripts\python.exe -m app.worker                                        # 解析 worker
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

### 4. 使用

1. 打开 `http://localhost:3000/upload`，上传一份 Markdown 学习资料，等状态变为 `done`
2. 打开 `/qa`，提问（SSE 流式展示 + 来源引用）
3. 打开 `/practice`，输入主题出题 → 作答 → 结构化批改

## MCP Server

StudyOS 把 `record_mistake` / `update_mastery` / `create_study_plan` 三个工具同时以两条路径暴露：
- **Function Calling**：项目自带 `/api/agent/run` 的 Agent 循环使用；
- **MCP**：`backend/app/mcp_server.py` 用官方 `mcp` SDK 封装为标准协议，任何支持 MCP 的客户端可接入。

`tools/list` 返回的参数定义与 Function Calling 路径一致（同一套参数模型），工具执行复用同一持久化逻辑。

### 启动 Server

```bash
cd backend
.venv\Scripts\python.exe -m app.mcp_server        # 默认 stdio 传输
```

### 用支持 MCP 的客户端连接

例如 Claude Code 或 Claude Desktop 把 StudyOS 配成 stdio MCP server：

```json
{
  "mcpServers": {
    "studyos": {
      "command": "D:\\Myknowledge\\studyos\\backend\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.mcp_server"],
      "cwd": "D:\\Myknowledge\\studyos\\backend"
    }
  }
}
```

### 与 Function Calling 的关系

Function Calling 是模型在 API 层的能力（模型能输出结构化工具调用）；MCP 是工具定义与调用的通信标准。MCP Server 暴露的工具定义经客户端塞给模型后，最终仍是模型的 Function Calling 能力在驱动；两者是"能力"与"标准"的关系，不是替代。

### 自测

```bash
cd backend
.venv\Scripts\python.exe test_mcp.py     # initialize / tools/list / tools/call 合法与非法参数
```

## API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/documents` | 上传文档（multipart `file`），入队异步解析 |
| GET | `/api/documents` | 文档列表与解析状态 |
| POST | `/api/qa/ask` | 带引用问答（JSON，含缓存） |
| POST | `/api/qa/stream` | SSE 流式问答：`meta`(来源) → `delta`(逐段) → `done` |
| POST | `/api/practice/generate` | 基于知识库出题 `{topic}` |
| POST | `/api/practice/answer` | 提交答案并结构化批改 `{question_id, answer}` |
| POST | `/api/agent/run` | Agent 意图路由 + 工具调用 `{message}` |
| GET | `/api/agent/knowledge-points` | 知识点掌握度（验证工具状态持久化） |
| GET | `/api/agent/mistakes` | 错题记录 |
| GET | `/api/agent/plans` | 学习计划 |

## 评测

先导入与评测集主题相关的资料，然后：

```bash
cd backend
.venv\Scripts\python.exe run_eval.py            # Recall@K / MRR
.venv\Scripts\python.exe run_eval.py --citations  # 额外跑引用正确性/完整性（调用 DeepSeek）
```

评测集在 `backend/eval/eval_set.json`，每条含：问题、预期来源关键词、预期知识点、关键答案要点、不应出现的结论。

## 目录结构

```
studyos/
├── backend/
│   ├── app/
│   │   ├── api/           # 路由层 (documents/qa/practice/agent)
│   │   ├── services/      # 解析/分块/入库/检索/问答/批改/评测/队列
│   │   ├── agent/         # 工具注册表 + 意图路由循环
│   │   ├── llm/           # DeepSeek 封装 (chat/stream/JSON/Function Calling) + 调用日志
│   │   └── models/        # SQLAlchemy 模型 (11 张表)
│   ├── eval/              # 20 题评测集
│   ├── run_eval.py        # 评测入口
│   ├── migrate.py         # 开发期轻量迁移
│   └── requirements.txt
├── frontend/              # Next.js (upload/qa/practice)
└── docker-compose.yml     # PostgreSQL(pgvector) + Redis
```
