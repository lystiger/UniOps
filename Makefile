.PHONY: install migrate api frontend test lint build fixture-sync

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

lint:
	uv run ruff check backend
	cd frontend && npm run lint

build:
	cd frontend && npm run build

fixture-sync:
	uv run uniops sync-easybooks --fixture backend/tests/fixtures/easybooks_bundle.json
