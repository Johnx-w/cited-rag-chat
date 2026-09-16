# 部署上线

## 0. 先看清要部署的是什么

这个仓库不是单进程应用，直接点「Deploy」起不来。

| 进程 | 作用 | 需要什么 |
| --- | --- | --- |
| Next.js | 登录、聊天 UI、把模型与工具串起来 | Node 24、Postgres、公网 HTTPS |
| Python 知识库 | 入库、混合检索、工具执行 | Python 3.13、**可写磁盘** |
| Postgres | 用户、会话、消息 | 托管库或容器 |

两个进程通过 `PYTHON_RAG_URL` 通信。关键点：**Python 侧是有状态的**，Chroma 向量库与
BM25 语料落在 `python/indexes/`，容器一重建就要重新灌语料。这是部署最容易翻车的地方。

原先仓库里只有一份「只起 Postgres」的 `docker-compose.yml`，没有 Dockerfile。
本次补齐了这些文件：

- `Dockerfile` —— Next.js 镜像。`target: runtime` 跑服务，`target: builder` 用来跑一次性迁移
- `python/Dockerfile` —— 知识库镜像，构建期已预热本地 MiniLM
- `docker-compose.prod.yml` —— 全栈自托管编排
- `deploy/Caddyfile`、`deploy/stack.env.example`、`deploy/web.env.example`、
  `deploy/python.env.example`、`deploy/render.yaml`
- `.dockerignore`（根与 `python/`）、`.gitignore` 增补 `deploy/*.env`

### 上线前必须知道的一件事：Python 服务默认没有鉴权

`python/app/server.py` 原本不校验任何身份。只要把 8000 端口放到公网：

- `POST /ingest` —— 任何人都能往你磁盘写文件、污染知识库
- `POST /tools/invoke` —— 任何人都能触发你的工具
- `GET /traces` —— 任何人都能读走你全部问答记录

本次加了一个开关式闸门 `INTERNAL_TOKEN`：**设了**则除 `/health` 外所有请求都要求
`X-Internal-Token` 一致，否则 401；Next.js 侧读同一个环境变量名并自动带上该请求头
（`lib/rag/python.ts`）。**不设**则完全不校验，本地开发行为与之前一模一样。

- 方案 A（Python 在公网）→ **必须设**
- 方案 B（Python 只在 Compose 内网）→ 不用设

另外顺手加了个 `BOOTSTRAP_INGEST` 开关：设为 `1` 时启动阶段发现索引为空就用
`data/sample` 重新灌一次，失败只打日志不阻断启动。给没有持久盘的托管环境兜底。

---

## 方案 A：¥0 起步，Vercel + Neon + 托管知识库

适合想先拿到一个能点开的链接、不想管服务器。三步各管一件事。

### A-1 Postgres：Neon

1. 注册 [neon.tech](https://neon.tech) → New Project，Region 选 **Singapore**（离国内近）。
2. 复制连接串。Neon 给两条：**Pooled** 和 **Direct**。
3. `POSTGRES_URL` 请用 **Direct** 那条 —— Pooled 走 PgBouncer，drizzle 迁移里的 DDL
   在事务中可能失败。连接串末尾带 `?sslmode=require`。

免费档够用：0.5 GB 存储，对这个应用绰绰有余。

### A-2 知识库服务：Hugging Face Spaces（免费、Docker）

Spaces 免费档给 2 vCPU / 16 GB 内存，比 Render free 宽裕得多，而且休眠门槛是 48 小时
无请求（Render free 是 15 分钟），对演示友好得多。

1. [huggingface.co](https://huggingface.co) → New → **Space** → SDK 选 **Docker** →
   名字例如 `cited-rag-knowledge` → 可见性选 Public。
2. 把本仓库 `python/` 目录当作 Space 仓库的根推上去：

```bash
cd python
git init
git remote add space https://huggingface.co/spaces/<你的HF用户名>/cited-rag-knowledge
git add .
git commit -m "deploy knowledge service"
git push space main
```

   `python/README.md` 里已经有 Spaces 需要的元数据（`sdk: docker`、`app_port: 8000`），
   不用改；它同时也就是本目录的说明文档。
3. 进 Space → **Settings → Variables and secrets**，加上：

| 名称 | 值 |
| --- | --- |
| `INTERNAL_TOKEN` | 一串长随机值（生成：`openssl rand -hex 24`） |
| `LLM_API_KEY` | 你的 DeepSeek key |
| `LLM_BASE_URL` | `https://api.deepseek.com` |
| `LLM_MODEL` | `deepseek-chat` |
| `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | 有向量网关就填，没有留空 |
| `BOOTSTRAP_INGEST` | **`1`** ← Space 没有持久盘，必须开 |

   `EMBEDDING_*` 留空会自动 fail-open 到镜像里已预热好的本地 MiniLM。效果够演示用，
   但入库和检索都要跑 CPU，语料大了会慢。想更稳就买个支持 OpenAI 兼容 embedding 的
   网关（智谱、硅基流动、阿里百炼都行）。
4. 等构建结束，访问 `https://<用户名>-<space名>.hf.space/health`，应返回
   `{"ok": true, "service": "cited-rag-knowledge", ...}`。

### A-3 Next.js：Vercel

1. [vercel.com](https://vercel.com) → Add New → Project → 导入 `Johnx-w/cited-rag-chat`。
   Framework 会自动识别成 Next.js，**Root Directory 保持仓库根**。
2. 加环境变量（Production 和 Preview 都勾上）：

| 名称 | 值 |
| --- | --- |
| `AUTH_SECRET` | `node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"` |
| `POSTGRES_URL` | Neon 的 Direct 连接串 |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | `deepseek-chat` |
| `PYTHON_RAG_URL` | Space 的地址，如 `https://xxx-cited-rag-knowledge.hf.space` |
| `INTERNAL_TOKEN` | 与 Space 上的**完全一致** |
| `REDIS_URL` | 选填。填 Upstash 免费 Redis 就能打开 IP 限流 |
| `BLOB_READ_WRITE_TOKEN` | 选填。填 Vercel Blob 才能传聊天图片附件 |

3. Deploy。注意 `package.json` 的 build 脚本是 `tsx lib/db/migrate && next build`，
   **构建期就会连库跑迁移**，所以 `POSTGRES_URL` 必须在构建时可用（Vercel 的环境变量
   默认构建时可见，满足）。
4. 部署完打开域名 → 登录页点 guest 直接进（不需要注册）→ 进 `/knowledge` 点
   「导入示例语料」。

### A-3 备选：用 Render 托管知识库

仓库里已经有 `deploy/render.yaml`，Render 控制台 → New → Blueprint → 选仓库即可。

两个提醒：Render 的持久磁盘**只对付费实例开放**（starter ≈ $7/月）；用 free 档就要删掉
`disk` 段并把 `BOOTSTRAP_INGEST` 改成 `1`，代价是上传的文档每次重启丢失、演示语料重建。
另外 free 档 15 分钟无请求即休眠，而 Next.js 侧对知识库的超时是 60 秒，演示前记得先手动
访问一次 `/health` 预热。

---

## 方案 B：一台中国香港轻量服务器，全栈自托管

适合想要一个地址管到底、不被三家平台的环境变量和三份日志来回折腾的情况。
**免备案**（香港节点），一个月三十几块，Python 完全不暴露到公网。

### B-1 买机器和域名

- 服务器：腾讯云 / 阿里云「轻量应用服务器」，地域选 **中国香港**，2 核 4G 起，
  约 ¥30–40/月。2 核 2G 也能跑（Chroma + MiniLM 约 1.2G 内存，Next 约 0.4G），
  但镜像构建阶段会比较紧张，建议 4G。
- 域名：任意便宜后缀（`.top` / `.xyz` 约 ¥10–30/年），加一条 A 记录指向服务器公网 IP。
- 安全组放行 **22 / 80 / 443**。

### B-2 装 Docker

```bash
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

### B-3 拉代码、填三份 env

```bash
git clone https://github.com/Johnx-w/cited-rag-chat.git
cd cited-rag-chat
cp deploy/stack.env.example  deploy/stack.env
cp deploy/web.env.example    deploy/web.env
cp deploy/python.env.example deploy/python.env
```

生成密钥（服务器上没装 node 就用第二条）：

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
openssl rand -base64 32 | tr -d '/+=' | cut -c1-43
```

要填的内容：

- `deploy/stack.env` —— `SITE_DOMAIN`（你的域名）、`POSTGRES_PASSWORD`（长随机值）
- `deploy/web.env` —— `AUTH_SECRET`、`POSTGRES_URL`（里面的密码要和上面一致）、
  `DEEPSEEK_API_KEY`。`PYTHON_RAG_URL` 保持 `http://python:8000`，`INTERNAL_TOKEN` **留空**
- `deploy/python.env` —— `LLM_API_KEY`。`INTERNAL_TOKEN` **留空**、`BOOTSTRAP_INGEST=0`

三份 `*.env` 都已被 `.gitignore`，不会误提交。

### B-4 起栈

```bash
docker compose -f docker-compose.prod.yml --env-file deploy/stack.env up -d --build
docker compose -f docker-compose.prod.yml logs -f caddy
```

首次要构建 Next.js 镜像，几分钟。Caddy 自动申请 Let's Encrypt 证书（前提是域名已解析到
本机、80/443 可达）；日志里出现证书签发成功后即可访问 `https://你的域名`。

编排顺序是有意的：`postgres` 健康 → `migrate` 跑完迁移并退出 → `web` 才启动。
Python 服务只用 `expose`、不做端口映射，所以公网访问不到它的任何接口。

### B-5 灌语料

登录后进 `/knowledge` 点「导入示例语料」即可，对应 `POST /api/knowledge/ingest-sample`。

---

## 上线前自测清单

逐条点一遍，别只看首页能打开：

- [ ] `https://你的域名` 打开是登录页，点 guest 能进
- [ ] 问一个笔记里有答案的问题（如 AlphaCore-7 相关）→ 回答带 `[n]` 引用，脚注有来源
- [ ] 问一个笔记里没有的问题 → 回答以「根据现有笔记无法确定。」开头
- [ ] 问出货金额一类的问题 → 走业务查询工具，数字**不带**笔记引用
- [ ] `/traces` 能看到刚才几轮的动作序列并可回放
- [ ] `/reports` 能出演示周报
- [ ] `curl https://<知识库地址>/health` 返回 ok
- [ ] `curl https://<知识库地址>/traces` **返回 401**（方案 A 必查；若返回数据说明闸门没生效）
- [ ] 手机关掉 Wi-Fi 用 4G 打开一次，确认是公网可达而不是只在本机通

## 成本对照

| 方案 | 组成 | 月成本 | 注意 |
| --- | --- | --- | --- |
| A 免费版 | Vercel Hobby + Neon Free + HF Spaces | ¥0 | 知识库 48h 无请求休眠 |
| A 省心版 | Vercel + Neon + Render starter | ≈ ¥50 | 最省事，有持久盘 |
| B | 中国香港轻量 2C4G + 域名 | ≈ ¥30–40 + 域名年费 | 一个地址管全部，Python 不暴露 |

## 常见坑

1. **知识库没有持久盘** —— 容器重启后 Chroma 索引丢失，表现是「刚才还能引用，现在全是
   无法确定」。方案 B 用 named volume（`pyindex` / `pyuploads` / `pytraces`）解决；
   托管环境设 `BOOTSTRAP_INGEST=1`。
2. **知识库休眠** —— 首个请求要等几十秒才出结果，而 Next 侧超时是 60 秒
   （`lib/rag/python.ts` 的 `AbortSignal.timeout(60_000)`）。演示前先打一次 `/health`。
3. **`INTERNAL_TOKEN` 两边不一致** —— 表现是页面 500、工具调用全失败，Python 日志里是
   401。这是全流程唯一需要改两处的地方。
4. **迁移失败** —— Neon 的 Pooled 连接串在 DDL 上可能出问题，换 Direct 连接串。
5. **本地能跑、线上报 UntrustedHost** —— 不用管，`app/(auth)/auth.config.ts` 里已经
   `trustHost: true`。
6. **上传大 PDF 失败** —— `deploy/Caddyfile` 的 `request_body` 限了 20MB，要放宽改那里。
7. **别把 `.env.local` 打进镜像** —— `lib/db/migrate.ts` 用 dotenv 读 `.env.local`，
   容器里没这个文件时 dotenv 静默跳过、退回读容器环境变量，这是预期行为。

## 上线之后

README 里那句「没有上线、没有用户量」可以改成实际域名了。但**别顺手把「离线评测 29 题」
写成生产指标** —— 招聘官真会点开追问，而这份诚实度本身是你现在的加分项。
