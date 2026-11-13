# ==============================================================================
# Michito Web Client SPA — Production Multi-Stage Dockerfile
# Node 20 Builder • Nginx Alpine Runner • Single-Page App Reverse Proxy
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Compile React Vite Assets
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy root workspace and client package manifests
COPY package*.json ./
COPY clients/web/package*.json ./clients/web/

# Install dependencies cleanly
RUN npm ci --workspace=clients/web

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

# Copy custom Nginx configuration with /api reverse proxy and SPA routing
COPY clients/web/nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port 80
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

