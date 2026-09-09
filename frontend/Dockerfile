# ==============================================================================
# AegisOps Frontend Multi-Stage Dockerfile
# Stage 1: Build React + TypeScript + Tailwind bundle
# Stage 2: Serve production assets via Nginx with API & WebSocket reverse proxy
# ==============================================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json* ./

# Install dependencies cleanly
RUN npm ci || npm install

# Copy source code and build config
COPY . .

# Build production assets (Vite output in /app/dist)
RUN npm run build

# --- Stage 2: Production Nginx Server ---
FROM nginx:alpine

# Remove default Nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy built frontend assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with reverse proxy for /api/ and /ws/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 inside container
EXPOSE 80

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
