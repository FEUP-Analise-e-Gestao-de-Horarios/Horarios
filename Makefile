.PHONY: dev mirror dev-mirror prod clean-db clean-db-volume clean-mirror local-setup

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
	docker compose -f docker-compose.dev.yml up --build

dev-mirror:
	docker compose -f docker-compose.dev.yml --profile mirror up --build

prod:
	docker compose -f docker-compose.prod.yml up --build

clean-db:
	rm -f databases/db.sqlite3
	rm -rf databases/projects/*

clean-db-volume:
	docker volume rm pi_db_data

clean-mirror:
	docker volume rm pi_mirror_data
