---
title: cited-rag-knowledge
emoji: 📚
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# cited-rag-knowledge

`cited-rag-chat` 的知识库服务：FastAPI + Chroma + BM25(jieba) + RRF，工具统一走
`invoke_tool` 以便每次观测前都过 PreToolUse 闸门。聊天 UI 在 Next.js 侧，这里只有 API。

上面那段 YAML 是 Hugging Face Spaces 的元数据。把本目录作为 Space 仓库的根推送上去，
Spaces 会用本目录的 `Dockerfile` 构建并暴露 8000 端口，直接得到一个可被 Vercel 调用的
知识库后端。不需要 Spaces 时这段元数据没有副作用。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查。设了 `INTERNAL_TOKEN` 时这个端点仍免鉴权，供探针使用 |
| POST | `/retrieve` | 混合检索 |
| POST | `/tools/invoke` | 工具统一入口，先过 PreToolUse |
| POST | `/ingest` | 上传 md / pdf 入库（multipart） |
| POST | `/ingest-sample` | 用 `data/sample` 重新播种语料 |
| GET | `/files` | 已索引文件清单 |
| GET | `/reports/weekly` | 演示周报 |
| GET / POST | `/traces`、`/traces/{id}`、`/traces/start`、`/traces/{id}/finish` | JSONL Trace 读写 |

## 两个部署开关

- **`INTERNAL_TOKEN`**：设了以后，除 `/health` 外所有请求都要带 `X-Internal-Token`
  头且值相等，否则 401。只有在**本服务对公网开放**时才需要设置——因为
  `/ingest` 能写盘、`/tools/invoke` 能触发工具、`/traces` 能读全部问答记录，
  裸奔在公网上等于把这三个口子交给所有人。留空则完全不校验，本地开发行为不变。
  Next.js 侧读同一个环境变量名并自动带上请求头（见 `lib/rag/python.ts`）。
- **`BOOTSTRAP_INGEST`**：设为 `1` 时，启动阶段若发现 Chroma 索引为空，就用
  `data/sample` 重新灌一次，失败只打日志不阻断启动。给没有持久盘的托管环境
  （Render free、Hugging Face Spaces）用，保证冷启动后仍有语料可问。

## 有状态目录

下面四个目录是有状态的，容器部署时要用卷挂载，别指望镜像里带：

```
indexes/           Chroma 向量库 + BM25 语料（可用 CHROMA_PATH 覆盖 Chroma 位置）
data/uploads/      用户上传的 md / pdf
traces/            JSONL Trace
data/demo/         演示 SQLite，首次访问自动建表播种，无需预置
```

## 本地运行

本目录（不是仓库根）执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

镜像构建（构建上下文是本目录）：

```bash
docker build -t cited-rag-knowledge .
docker run --rm -p 8000:8000 --env-file .env -v "$PWD/indexes:/srv/indexes" cited-rag-knowledge
```

## 测试

```powershell
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\run_eval.py --backend fake
```
