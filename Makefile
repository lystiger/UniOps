.PHONY: install migrate api frontend test test-pg lint build fixture-sync db-up db-down backup

install:
	uv sync --all-groups
	cd frontend && npm install

migrate:
	uv run alembic upgrade head

api:
	uv run uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

test:
	uv run pytest
	cd frontend && npm test

# The same suite against the deployment database. Needs `make db-up` first.
test-pg:
	UNIOPS_TEST_DATABASE_URL=postgresql+psycopg://uniops:$(UNIOPS_DB_PASSWORD)@127.0.0.1:5432/uniops \
		uv run pytest

lint:
	uv run ruff check backend
	cd frontend && npm run lint

build:
	cd frontend && npm run build

fixture-sync:
	uv run uniops sync-easybooks --fixture backend/tests/fixtures/easybooks_bundle.json

db-up:
	docker compose up -d db

db-down:
	docker compose down

backup:
	scripts/backup.sh
