# cited-rag-chat

可登录的内部知识 / 研究助手。本仓库**不是**从零写的聊天产品：前端工程壳来自 [vercel/chatbot](https://github.com/vercel/chatbot)，检索、强制引用、JSONL Trace、离线评测和工具权限闸门才是本仓库要实现的业务。

GitHub 上这是独立仓库 `Johnx-w/cited-rag-chat`，**不是**官方 fork 展示页。本地保留 `upstream` 指向官方模板，便于对照，不用于对外展示。

## 对照 vercel/chatbot

| 部分 | 来源 | 状态 |
| --- | --- | --- |
| Next.js App Router、AI SDK 流式、Auth.js、Postgres 会话、聊天 UI | 官方模板 | 保留 |
| `get-weather`、官方 Artifacts 作为默认工具 | 官方模板 | 阶段 1 已从聊天工具里移除 |
| 知识库入库 / `retrieve_knowledge` / 引用与拒答 | 迁自已有 RAG + Tool Calling（Python，不是 TS 重写） | 阶段 1 |
| calculator / 时间 / `find_indexed_file` / PreToolUse 闸门 | 迁自 RAG 工具 + Hearth PreToolUse 机制 | 阶段 2 |
| JSONL Trace、FakeClient 离线评测 | 已有评测口径 | 阶段 3 |
| 只读 SQLite、演示周报、FastMCP | 已有 RAG 第二期机制 | 阶段 4 |


## 当前进度

**阶段 4**：在阶段 2 四个工具之外增加 `query_business_data`（只读演示 SQLite）和 `generate_weekly_report`（固定 SELECT 出演示周报）。SQL 工具名白名单只放行 `query_business_data`；`execute_sql` / 未列出的 SQL 仍拒绝。非法 SQL 以 error JSON 回灌模型，不写库。侧栏 **Reports** 打开 `/reports` 生成演示周报。FastMCP stdio 只暴露 `retrieve_knowledge`，内部仍走 `invoke_tool` / PreToolUse。

阶段 1–3 仍然有效：登录、DeepSeek 流式、知识库引用/拒答、四类基础工具、JSONL Trace、FakeClient 冻结集。阶段 4 **没有**把 SQL/周报题塞进冻结集。向量 Key 不足时仍 fail-open 到本地 MiniLM。

没有把 Streamlit 搬进 Next.js。没有真 IMAP、LangGraph、GraphRAG、浏览器操作 Agent。没有上线、没有用户量。

## 本地运行（Windows / PowerShell）

不要求先做 Vercel 生产部署。需要两个进程：Next.js（3000）+ Python 知识库（8000）。

### 1. 依赖

- Node.js 24+、pnpm 10+
- Python 3.13
- 本机没有 Docker Desktop 时，可用 **WSL Docker** 跑 Postgres

### 2. 环境变量

`.env.local`（gitignore）：

| 变量 | 作用 |
| --- | --- |
| `AUTH_SECRET` | Auth.js 会话密钥 |
| `POSTGRES_URL` | 会话与用户。本机用 WSL IP + **5433** |
| `DEEPSEEK_API_KEY` | DeepSeek 聊天。直连 `https://api.deepseek.com` |
| `DEEPSEEK_BASE_URL` | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 默认 `deepseek-chat` |
| `PYTHON_RAG_URL` | 默认 `http://127.0.0.1:8000` |
| `REDIS_URL` | 未设：无限流、无 resumable stream |
| `BLOB_READ_WRITE_TOKEN` | 未设：聊天图片附件失败。知识库上传不走 Blob |

`python/.env`（gitignore）：聊天 Key 可与 DeepSeek 相同；**向量默认另配** `EMBEDDING_*`（DeepSeek 没有 embedding API）。智谱等向量网关余额不足时，入库/检索会 fail-open 到 Chroma 自带的本地 MiniLM；BM25（jieba）+ RRF 机制不变。Rerank 无 Key 同样 fail-open。

### 3. Postgres

```powershell
Get-Content -Raw .pg.env | wsl -e bash -lc "cat > /tmp/cited-pg.env"
$wslDir = wsl wslpath -a $PWD
wsl -e bash -lc "cd `"$wslDir`" && docker compose up -d"
node .\scripts\set-pg-url.mjs
node .\scripts\pg-ping.mjs
```

### 4. Python 知识库服务

```powershell
py -3.13 -m venv python\.venv
.\python\.venv\Scripts\python.exe -m pip install -U pip
.\python\.venv\Scripts\python.exe -m pip install -r python\requirements.txt
# 配置 python/.env 后：
.\python\.venv\Scripts\python.exe -m uvicorn app.server:app --app-dir python --host 127.0.0.1 --port 8000
```

检查：`http://127.0.0.1:8000/health`

### 5. Next.js

```powershell
pnpm install
pnpm db:migrate
pnpm dev
```

- 登录：[http://localhost:3000/login](http://localhost:3000/login)
- 知识库：[http://localhost:3000/knowledge](http://localhost:3000/knowledge)
- 演示周报：[http://localhost:3000/reports](http://localhost:3000/reports)
- Trace 回放：[http://localhost:3000/traces](http://localhost:3000/traces)
- 聊天：建议问句覆盖检索、演示库出货、演示周报、当前时间。文档题应变引用 `[n]` 或「根据现有笔记无法确定。」演示库数字不要写成笔记引用。

闸门自测（Python）：

```powershell
cd python
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 6. 评测

```powershell
cd python
.\.venv\Scripts\python.exe scripts\run_eval.py --backend fake
```

冻结集快照见 `docs/eval-baseline.md`。这是离线题量，不要写成生产指标。

### 7. FastMCP（stdio）

只暴露 `retrieve_knowledge`。从仓库根目录：

```powershell
.\scripts\start-mcp.ps1
```

或在 `python/` 目录：

```powershell
.\.venv\Scripts\python.exe -m src.mcp_server
```

这是给其他 MCP 客户端用的 stdio 服务，不是浏览器页。执行前仍走 PreToolUse，不会另开写文件/Shell 通道。

## 仓库远程

```
origin    https://github.com/Johnx-w/cited-rag-chat.git
upstream  https://github.com/vercel/chatbot.git
```

## 参考（只迁机制，不搬 UI）

- 检索实现：[Johnx-w/RAG-Tool-Calling-Agent](https://github.com/Johnx-w/RAG-Tool-Calling-Agent)
- 工具权限闸门：[Johnx-w/hearth-harness](https://github.com/Johnx-w/hearth-harness)
