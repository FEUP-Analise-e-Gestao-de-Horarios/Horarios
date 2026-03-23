.PHONY: dev mirror dev-mirror prod clean-db clean-db-volume clean-mirror local-setup deploy deploy-build deploy-push deploy-run

REMOTE_HOST ?= horarios@10.227.107.115
REMOTE_DIR  ?= /opt/horarios
IMAGE_NAME  ?= horarios-app

local-setup:
	@echo "--- Checking required tools ---"
	@command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
	@command -v pipenv >/dev/null 2>&1 || { echo "ERROR: pipenv not found. Install with: pip install pipenv"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }
	@command -v pre-commit >/dev/null 2>&1 || { echo "ERROR: pre-commit not found. Install with: pip install pre-commit (or pipenv install --dev from backend/)"; exit 1; }
	@echo "All required tools found."
	@echo ""
	@echo "--- Installing backend dependencies (pipenv) ---"
	cd backend && pipenv install --dev
	@echo ""
	@echo "--- Installing frontend dependencies (npm) ---"
	cd frontend && npm install
	@echo ""
	@echo "--- Installing git pre-commit hooks ---"
	pre-commit install
	@echo ""
	@echo "Local setup complete."

mirror:
	docker compose -f docker-compose.dev.yml --profile mirror up --build mirror

dev:
	mkdir -p databases/projects
	docker compose -f docker-compose.dev.yml up --build

dev-mirror:
	mkdir -p databases/projects
	docker compose -f docker-compose.dev.yml --profile mirror up --build

prod:
	docker compose -f docker-compose.prod.yml up --build

clean-db:
	rm -rf databases/

clean-db-volume:
	docker volume rm pi_db_data

clean-mirror:
	docker volume rm pi_mirror_data

deploy-build:
	docker compose -f docker-compose.prod.yml build

deploy-push:
	@echo "--- Sending image to $(REMOTE_HOST) ---"
	docker save $(IMAGE_NAME) | gzip | ssh $(REMOTE_HOST) "gunzip | docker load"
	@echo "--- Sending compose file and env ---"
	ssh $(REMOTE_HOST) "mkdir -p $(REMOTE_DIR)"
	scp docker-compose.prod.yml $(REMOTE_HOST):$(REMOTE_DIR)/docker-compose.prod.yml
	scp backend/.env $(REMOTE_HOST):$(REMOTE_DIR)/.env
	@echo "--- Done ---"

deploy-run:
	ssh $(REMOTE_HOST) "cd $(REMOTE_DIR) && docker compose -f docker-compose.prod.yml up -d"

deploy: deploy-build deploy-push deploy-run
	@echo "--- Deployed successfully ---"
