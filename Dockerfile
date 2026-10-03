# Multi-stage Dockerfile for Sentinel

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Lint, type-check and build the frontend (fails the image build on problems)
RUN npm run lint && npm run build

# Stage 2: Backend tests. The image build (and so CI) fails if they fail.
FROM python:3.12-slim AS backend-tests

WORKDIR /app

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY backend/ ./
RUN python -m pytest -q -p no:cacheprovider && touch /tests-passed

# Stage 3: Python backend
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source (tests ran in the backend-tests stage)
COPY backend/ ./
RUN rm -rf tests requirements-dev.txt
# Depend on the test stage so BuildKit doesn't skip it
COPY --from=backend-tests /tests-passed /tmp/tests-passed

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./data/sentinel.db

# Expose port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

# Use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
