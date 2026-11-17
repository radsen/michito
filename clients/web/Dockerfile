# ==============================================================================
# Michito Web Client SPA — Production Multi-Stage Dockerfile
# Node 20 Builder • Nginx Alpine Runner • Single-Page App Reverse Proxy
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Compile React Vite Assets
# ------------------------------------------------------------------------------
FROM node:20-slim AS builder

WORKDIR /app

# Copy root workspace and client package manifests
COPY package*.json ./
COPY clients/web/package*.json ./clients/web/

# Install dependencies cleanly and ensure Linux Rollup binary is present
RUN npm ci --workspace=clients/web && npm install -D @rollup/rollup-linux-x64-gnu --workspace=clients/web

# Copy web client source code
COPY clients/web/ ./clients/web/

# Build production bundle (tsc && vite build)
RUN npm run build --workspace=clients/web

# ------------------------------------------------------------------------------
# Stage 2: Minimal Nginx Alpine Production Web Server
# ------------------------------------------------------------------------------
FROM nginx:alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA bundle from builder stage
COPY --from=builder /app/clients/web/dist /usr/share/nginx/html

# Copy custom Nginx configuration template for dynamic environment substitution
COPY clients/web/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY clients/web/nginx.conf /etc/nginx/conf.d/default.conf

# Copy robust custom startup script and disable conflicting default entrypoints
COPY clients/web/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && rm -f /docker-entrypoint.d/20-envsubst-on-templates.sh

# Default environment variables for runtime substitution
ENV PORT=8080 \
    BACKEND_URL=http://api:8000

# Expose HTTP port
EXPOSE 80 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:${PORT}/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]

