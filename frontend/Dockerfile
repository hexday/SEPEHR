# SEPEHR Frontend — Dockerfile
# Multi-stage build for minimal production Next.js image

FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

# ── Builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_WS_URL=""
ARG NEXT_PUBLIC_MINIO_HOST="localhost"
ARG NEXT_PUBLIC_MINIO_PORT="9000"

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_MINIO_HOST=$NEXT_PUBLIC_MINIO_HOST
ENV NEXT_PUBLIC_MINIO_PORT=$NEXT_PUBLIC_MINIO_PORT
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Production image ──────────────────────────────────────────────────────────
FROM base AS production
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy built output
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
