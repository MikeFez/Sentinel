# Makefile Commands Reference

Sentinel uses a Docker-focused Makefile for simplified deployment and management.

## Quick Reference

```bash
make help          # Show all available commands
make start         # Start Sentinel
make stop          # Stop Sentinel
make logs          # View logs
make status        # Check status
```

## Complete Command List

### General

| Command | Description |
|---------|-------------|
| `make help` | Display help message with all commands |
| `make info` | Show project information and stack |

### Docker Operations

| Command | Description |
|---------|-------------|
| `make docker-build` | Build Docker image |
| `make docker-up` | Start Docker containers (detached) |
| `make docker-down` | Stop Docker containers |
| `make docker-logs` | View Docker logs (follow mode) |
| `make docker-restart` | Restart Docker containers |
| `make docker-rebuild` | Rebuild and restart containers |
| `make docker-shell` | Open bash shell in running container |
| `make docker-exec CMD="..."` | Run command in container |

### Quick Aliases

| Command | Description |
|---------|-------------|
| `make start` | Start Sentinel (alias for docker-up) |
| `make stop` | Stop Sentinel (alias for docker-down) |
| `make restart` | Restart Sentinel (alias for docker-restart) |
| `make deploy` | Deploy/redeploy (alias for docker-rebuild) |
| `make logs` | View logs (alias for docker-logs) |

### Database Management

| Command | Description |
|---------|-------------|
| `make db-backup` | Backup database to `backups/` directory |
| `make db-restore` | Restore from latest backup |
| `make db-reset` | Reset database (deletes all data!) |

### Monitoring

| Command | Description |
|---------|-------------|
| `make status` | Check Docker container and database status |

### Cleanup

| Command | Description |
|---------|-------------|
| `make clean` | Clean Docker system and build cache |

## Common Workflows

### First Time Setup

```bash
# Start Sentinel for the first time
make start

# View logs to confirm it's running
make logs
```

### Daily Usage

```bash
# Start
make start

# Check status
make status

# View logs
make logs

# Stop
make stop
```

### Updates and Rebuilds

```bash
# After pulling code changes
make deploy

# Or manually:
make docker-rebuild
```

### Database Management

```bash
# Backup before major changes
make db-backup

# Reset database (if needed)
make db-reset

# Restore from backup (if needed)
make db-restore
```

### Troubleshooting

```bash
# Check what's running
make status

# View logs
make logs

# Get a shell inside the container
make docker-shell

# Run a command in the container
make docker-exec CMD="ls -la /app"

# Full restart
make restart

# Clean rebuild
make clean
make deploy
```

## Docker-First Approach

This Makefile is designed for **Docker-only deployment**:

- ✅ All dependencies are installed inside the container
- ✅ No need for local Python venv or Node.js setup
- ✅ Consistent environment across machines
- ✅ Simple one-command deployment

### What Happens When You Start

When you run `make start` (or `make docker-up`):

1. Docker Compose builds the image (if not already built)
2. Multi-stage build compiles frontend
3. Backend dependencies are installed
4. Container starts and runs migrations automatically
5. FastAPI serves the built frontend

### Accessing the Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: Persisted in `./data/sentinel.db` (volume mounted)

## Tips

1. **First Time**: Just run `make start` and you're good to go
2. **Check Status**: Run `make status` to see if containers are running
3. **View Logs**: Use `make logs` to monitor activity
4. **Shell Access**: Use `make docker-shell` to debug inside the container
5. **Clean Restart**: `make clean && make deploy` for a fresh start

## Environment Variables

Override settings when running commands:

```bash
# Custom LLM endpoint
LLM_BASE_URL=http://custom.lan:8080/v1 make docker-up

# Different model
LLM_MODEL=llama3 make deploy
```

Or edit `docker-compose.yml` to persist changes.

## Troubleshooting

### Container Won't Start

```bash
# Check what's wrong
make status
make logs

# Try cleaning and rebuilding
make clean
make docker-rebuild
```

### Port Already in Use

```bash
# Check what's using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill -9

# Restart
make restart
```

### Database Issues

```bash
# Backup first
make db-backup

# Reset database
make db-reset

# Restart container
make restart
```

### "Command not found"

- Make sure you're in the project root directory
- Check that `Makefile` exists: `ls -la Makefile`
- Ensure `make` is installed: `which make`

## Advanced Usage

### Running Commands in Container

```bash
# Check logs inside container
make docker-exec CMD="tail -f /app/app.log"

# Check database
make docker-exec CMD="ls -la /app/data"

# Run Python shell
make docker-exec CMD="python"
```

### Chaining Commands

```bash
# Stop, clean, rebuild, and view logs
make stop && make clean && make deploy && make logs
```

### Background Operations

All Docker containers run in detached mode by default. Use `make logs` to follow output.

## Quick Command Reference

| Task | Command |
|------|---------|
| Start app | `make start` |
| Stop app | `make stop` |
| Restart app | `make restart` |
| View logs | `make logs` |
| Check status | `make status` |
| Backup DB | `make db-backup` |
| Shell access | `make docker-shell` |
| Full rebuild | `make deploy` |
| Clean everything | `make clean` |
