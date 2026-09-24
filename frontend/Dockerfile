# syntax=docker/dockerfile:1

# Build stage: same Node version pinned in CI (.github/workflows).
FROM node:22.22.2-bookworm-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Baked in at build time (Vite env vars are compile-time, not runtime).
# A relative path so the browser calls the same origin nginx serves the
# app from -- nginx reverse-proxies /api/ to the backend service
# (nginx.conf), so no CORS configuration is needed for this deployment.
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# Runtime stage: static files behind nginx, nothing else.
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
