.PHONY: help docker-build docker-up docker-down docker-logs docker-restart docker-rebuild docker-shell docker-exec db-backup db-restore db-reset test clean status start stop restart deploy info logs

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)Sentinel - AI-Powered Stock Intelligence Dashboard$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Docker

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-up: ## Start Docker containers
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Sentinel is running at http://localhost:8000$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-logs: ## View Docker logs (follow mode)
	docker-compose logs -f

docker-restart: docker-down docker-up ## Restart Docker containers

docker-rebuild: docker-down docker-build docker-up ## Rebuild and restart containers

docker-shell: ## Open shell in running container
	docker-compose exec sentinel /bin/bash

docker-exec: ## Run command in container (usage: make docker-exec CMD="ls -la")
	docker-compose exec sentinel $(CMD)

logs: docker-logs ## Alias for docker-logs

##@ Database

db-backup: ## Backup database
	@echo "$(BLUE)Backing up database...$(NC)"
	@mkdir -p backups
	@cp data/sentinel.db backups/sentinel_$$(date +%Y%m%d_%H%M%S).db 2>/dev/null || echo "$(YELLOW)No database found to backup$(NC)"
	@echo "$(GREEN)✓ Database backed up to backups/$(NC)"

db-restore: ## Restore database from latest backup
	@echo "$(YELLOW)Restoring database from latest backup...$(NC)"
	@cp $$(ls -t backups/sentinel_*.db | head -1) data/sentinel.db
	@echo "$(GREEN)✓ Database restored$(NC)"
	@echo "$(YELLOW)Note: Restart container for changes to take effect$(NC)"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)⚠️  WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f data/sentinel.db; \
		echo "$(GREEN)✓ Database deleted. Restart container to reinitialize.$(NC)"; \
	fi

##@ Cleanup

test: ## Run the backend tests (needs uv)
	cd backend && uv run --no-project --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m pytest -q

clean: ## Clean Docker system and build cache
	@echo "$(BLUE)Cleaning Docker build cache...$(NC)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✓ Cleaned$(NC)"

##@ Monitoring

status: ## Check status of services
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Sentinel Status$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@docker-compose ps 2>/dev/null || echo "  $(YELLOW)✗ Docker containers not running$(NC)"
	@echo ""
	@echo "Database:"
	@test -f data/sentinel.db && echo "  $(GREEN)✓ Database exists (data/sentinel.db)$(NC)" || echo "  $(YELLOW)○ No database found$(NC)"
	@echo ""

##@ Quick Start

start: docker-up ## Start Sentinel

stop: docker-down ## Stop Sentinel

restart: docker-restart ## Restart Sentinel

deploy: docker-rebuild ## Deploy/redeploy with Docker

##@ Information

info: ## Show project information
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Sentinel - AI-Powered Stock Intelligence Dashboard$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "Version: 1.0.0"
	@echo "Docker: $$(docker --version 2>/dev/null || echo '$(RED)Not installed$(NC)')"
	@echo ""
	@echo "Project stack:"
	@echo "  Backend:  FastAPI + Python 3.12+"
	@echo "  Frontend: React + TypeScript + Vite"
	@echo "  Database: SQLite (volume mounted)"
	@echo "  AI:       OpenAI-compatible endpoint (LLM_BASE_URL)"
	@echo ""
	@echo "Documentation:"
	@echo "  README.md       - Getting started"
	@echo "  DOCKER.md       - Docker deployment"
	@echo "  MAKEFILE.md     - Make commands reference"
	@echo ""
	@echo "URLs:"
	@echo "  Application: http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo ""
