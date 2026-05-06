.PHONY: dev mirror dev-mirror prod clean-db clean-db-volume clean-mirror local-setup deploy deploy-build deploy-push deploy-run

REMOTE_HOST ?= horarios@10.227.107.115
REMOTE_DIR  ?= /opt/horarios
IMAGE_NAME  ?= horarios-app

local-setup:
	@echo "--- Checking required tools ---"
	@command -v uv >/dev/null 2>&1 || { echo "ERROR: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }
	@echo "All required tools found."
	@echo ""
	@echo "--- Installing backend dependencies (uv) ---"
	cd backend && uv sync --frozen
	@echo ""
	@echo "--- Installing frontend dependencies (npm) ---"
	cd frontend && npm install
	@echo ""
	@echo "--- Installing git pre-commit hooks ---"
	cd backend && uv run pre-commit install
	@echo ""
	@echo "Local setup complete."

mirror:
	docker compose -f docker-compose.dev.yml --profile mirror up --build mirror

dev:
	mkdir -p databases/projects
	trap 'docker compose -f docker-compose.dev.yml down' EXIT INT TERM; \
	docker compose -f docker-compose.dev.yml up --build

dev-mirror:
	mkdir -p databases/projects
	docker compose -f docker-compose.dev.yml --profile mirror up --build

prod:
	docker compose -f docker-compose.prod.yml up --build

clean-db:
	rm -rf databases/

clean-db-volume:
	docker volume rm horarios_db_data

clean-mirror:
	docker volume rm horarios_mirror_data

deploy-build:
	docker compose -f docker-compose.prod.yml build

deploy-push:
	@echo "--- Sending image to $(REMOTE_HOST) ---"
	docker save $(IMAGE_NAME) | gzip | ssh $(REMOTE_HOST) "gunzip | docker load"
	@echo "--- Sending compose file and env ---"
	ssh $(REMOTE_HOST) "mkdir -p $(REMOTE_DIR)/backend"
	scp docker-compose.prod.yml $(REMOTE_HOST):$(REMOTE_DIR)/docker-compose.prod.yml
	scp backend/.env $(REMOTE_HOST):$(REMOTE_DIR)/backend/.env
	@echo "--- Done ---"

deploy-run:
	ssh $(REMOTE_HOST) "cd $(REMOTE_DIR) && docker compose -f docker-compose.prod.yml up -d"

deploy: deploy-build deploy-push deploy-run
	@echo "--- Deployed successfully ---"
