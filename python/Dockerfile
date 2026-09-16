# 知识库服务（FastAPI + Chroma + BM25）镜像。
#
# 构建上下文是 python/ 目录，不是仓库根目录：
#   docker build -f python/Dockerfile -t cited-rag-knowledge python
#
# 有状态目录（运行时用卷挂载，别写进镜像）：
#   /srv/indexes         Chroma 向量库 + BM25 语料
#   /srv/data/uploads    用户上传的 md / pdf
#   /srv/traces          JSONL trace
#   /srv/data/demo       演示 SQLite（首次访问自动建表播种）

FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# chromadb 的若干依赖在部分平台上没有 wheel，装编译工具兜底
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.13-slim AS runtime

# libgomp1 是 onnxruntime 的运行时依赖；curl 给 HEALTHCHECK 用
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/srv

WORKDIR /srv

# 只 COPY 预热脚本再跑，这样改业务代码不会让模型重新下载
COPY scripts/warmup_embeddings.py scripts/warmup_embeddings.py
RUN python scripts/warmup_embeddings.py

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# 用 python -m 而不是直接调 uvicorn：--prefix 安装的入口脚本 shebang 指向
# 构建阶段的 /install/bin/python，在运行镜像里不存在
CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
