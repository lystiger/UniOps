.PHONY: install migrate api frontend test test-e2e test-pg lint build ci fixture-sync db-up db-down backup deploy

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

# The browser suite. Builds the SPA and serves it with the API against a
# throwaway temp database seeded from the EasyBooks fixture; never a live sync.
test-e2e:
	cd frontend && npx playwright test

# The same suite against the deployment database. Needs `make db-up` first.
test-pg:
	UNIOPS_TEST_DATABASE_URL=postgresql+psycopg://uniops:$(UNIOPS_DB_PASSWORD)@127.0.0.1:5432/uniops \
		uv run pytest

lint:
	uv run ruff check backend
	cd frontend && npm run lint

build:
	cd frontend && npm run build

# What CI runs, in the same order, so a failure can be reproduced here first.
ci: lint build test test-e2e

# Pull a released tag onto the machine that runs UniOps. Not for a workstation.
deploy:
	scripts/deploy.sh $(TAG)

fixture-sync:
	uv run uniops sync-easybooks --fixture backend/tests/fixtures/easybooks_bundle.json

db-up:
	docker compose up -d db

db-down:
	docker compose down

backup:
	scripts/backup.sh
