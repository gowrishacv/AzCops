.PHONY: dev test lint migrate api-dev ui-dev db-up db-down clean

# Local development
dev: db-up api-dev

db-up:
	docker-compose up -d postgres

db-down:
	docker-compose down

api-dev:
	cd src/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ui-dev:
	cd src/ui && npm run dev

# Database
migrate:
	cd src/api && alembic upgrade head

migrate-down:
	cd src/api && alembic downgrade -1

migrate-create:
	cd src/api && alembic revision --autogenerate -m "$(msg)"

# Testing
test:
	cd src/api && python -m pytest tests/ -v --tb=short

test-cov:
	cd src/api && python -m pytest tests/ -v --tb=short --cov=app --cov-report=html --cov-report=term-missing

test-engine:
	cd src/engine && python -m pytest tests/ -v --tb=short --cov=rules --cov=scoring --cov-report=term-missing

# Linting
lint:
	cd src/api && ruff check . && ruff format --check .

lint-fix:
	cd src/api && ruff check --fix . && ruff format .

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down -v

# Terraform
tf-init:
	cd infra/terraform/environments/dev && terraform init

tf-plan:
	cd infra/terraform/environments/dev && terraform plan

tf-apply:
	cd infra/terraform/environments/dev && terraform apply

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
