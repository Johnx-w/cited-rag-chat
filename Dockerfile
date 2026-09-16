# Next.js 应用镜像（自托管用；部署到 Vercel 时不需要这个文件）。
#
# 构建上下文是仓库根目录：
#   docker build -f Dockerfile -t cited-rag-web .
#
# 两个用途，共用同一份 Dockerfile：
#   target: runtime  → 生产运行镜像，跑 node server.js
#   target: builder  → 带 node_modules 与源码，用来跑一次性数据库迁移
#                      （见 docker-compose.prod.yml 的 migrate 服务）
#
# 构建阶段刻意不注入 POSTGRES_URL：next build 期间不应该连库，迁移统一放到
# 容器启动后由 migrate 服务执行。

FROM node:24-alpine AS base

# Next.js 需要 libc6-compat；corepack 用来启用在 package.json 里锁定的 pnpm
RUN apk add --no-cache libc6-compat curl \
 && corepack enable
WORKDIR /app


FROM base AS deps

COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile


FROM base AS builder

COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_OUTPUT_STANDALONE=1
# 直接调 next build，跳过 package.json 里 build 脚本附带的 db:migrate
RUN pnpm exec next build


FROM base AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
# standalone 只会自动 trace import 到的文件，SQL 迁移目录是运行时读盘的，
# 必须手动带进来，否则 migrate 服务会因为找不到 migrations 而失败
COPY --from=builder --chown=node:node /app/lib/db/migrations ./lib/db/migrations

RUN mkdir -p .next/cache && chown -R node:node .next

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -fsS http://127.0.0.1:3000/api/health > /dev/null 2>&1 \
      || curl -fsS http://127.0.0.1:3000/ > /dev/null 2>&1 \
      || exit 1

CMD ["node", "server.js"]
