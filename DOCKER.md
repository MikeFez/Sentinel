# Docker Deployment Guide

This guide covers deploying Sentinel using Docker and Docker Compose.

## Quick Start

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The application will be available at http://localhost:8000

## Configuration

### Environment Variables

Create a `.env` file in the project root to customize settings:

```env
DATABASE_URL=sqlite:///./data/sentinel.db
OLLAMA_URL=http://athena.lan:11434
OLLAMA_MODEL=qwen2.5:14b
NEWS_ARTICLE_COUNT=10
```

Or modify `docker-compose.yml` directly.

### Ollama Connection

By default, Sentinel connects to Ollama at `http://athena.lan:11434`. Update this to match your Ollama server:

**Option 1: Environment Variable**
```yaml
environment:
  - OLLAMA_URL=http://your-ollama-host:11434
```

**Option 2: Docker Network** (if Ollama is also in Docker)
```yaml
services:
  sentinel:
    # ... existing config ...
    environment:
      - OLLAMA_URL=http://ollama:11434

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
```

## Data Persistence

The SQLite database is persisted in the `./data` directory, which is mounted as a volume:

```yaml
volumes:
  - ./data:/app/data
```

This ensures your data survives container restarts and rebuilds.

### Backup Database

```bash
# Backup
cp ./data/sentinel.db ./data/sentinel.db.backup

# Restore
cp ./data/sentinel.db.backup ./data/sentinel.db
docker-compose restart
```

## Building from Source

```bash
# Build the image
docker build -t sentinel:latest .

# Run manually
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e OLLAMA_URL=http://athena.lan:11434 \
  -e OLLAMA_MODEL=qwen2.5:14b \
  --name sentinel \
  sentinel:latest
```

## Multi-Stage Build Details

The Dockerfile uses a multi-stage build:

1. **Stage 1 (frontend-builder)**: Builds the React frontend with Vite
   - Uses Node 18 Alpine
   - Runs `npm run build`
   - Output: `/app/frontend/dist`

2. **Stage 2 (backend)**: Python backend with built frontend
   - Uses Python 3.12 slim
   - Installs Python dependencies
   - Copies built frontend from Stage 1
   - Runs FastAPI server serving both API and static files

## Port Configuration

By default, the container exposes port 8000. To use a different port:

```yaml
ports:
  - "3000:8000"  # Access on port 3000
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs sentinel

# Common issues:
# - Port 8000 already in use
# - Ollama URL unreachable
# - Database permission issues
```

### Can't connect to Ollama
```bash
# Test Ollama connectivity from container
docker-compose exec sentinel curl http://athena.lan:11434/api/tags

# If this fails, check:
# - Ollama is running
# - Firewall allows connections
# - Hostname resolves correctly
```

### Database locked
```bash
# Stop container
docker-compose down

# Check file permissions
ls -la ./data/sentinel.db

# Fix permissions if needed
chmod 644 ./data/sentinel.db
```

### Reset everything
```bash
# Stop and remove containers
docker-compose down

# Remove database
rm -rf ./data/*.db

# Rebuild and start
docker-compose up --build
```

## Production Deployment

### Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name sentinel.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d sentinel.yourdomain.com
```

### Auto-start on boot

```bash
# Enable Docker service
sudo systemctl enable docker

# Container will auto-restart with:
restart: unless-stopped
```

## Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up --build -d

# Check logs
docker-compose logs -f
```

## Resource Limits

To limit resource usage:

```yaml
services:
  sentinel:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Monitoring

```bash
# Container stats
docker stats sentinel

# Disk usage
du -sh ./data

# View recent logs
docker-compose logs --tail=100 -f
```
