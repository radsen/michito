.PHONY: help install dev dev-web dev-api dev-worker build test test-unit test-integration test-e2e test-playwright test-cov prospects stats pilot clean

PYTHON := ./venv/bin/python
PYTEST := ./venv/bin/pytest
UVICORN := ./venv/bin/uvicorn
PIP := ./venv/bin/pip

help:
	@echo "Michito Monorepo Commands:"
	@echo "  make install        Install Python backend & Node web dependencies"
	@echo "  make dev            Start full TMUX development environment (API, Web, Firebase, Worker)"
	@echo "  make dev-api        Run FastAPI backend directly (:8000)"
	@echo "  make dev-web        Run Vite React client directly (:3000)"
	@echo "  make dev-worker     Run async order worker daemon"
	@echo "  make build          Build React web client for production"
	@echo "  make test           Run complete automated test suite"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-e2e       Run end-to-end tests only"
	@echo "  make test-playwright Run Playwright browser UI E2E tests (with video/screenshots)"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make prospects      Run CLI prospector (usage: make prospects ARGS='--campaign=hebi --limit=10')"
	@echo "  make stats          Display deduplication ledger statistics"
	@echo "  make clean          Clean temporary build caches"

install:
	python3 -m venv venv || true
	$(PIP) install -r backend/requirements.txt
	npm install
	cd clients/web && npm install

dev:
	./start_dev_env.sh

dev-api:
	$(UVICORN) src.entrypoints.api.main:app --app-dir backend --reload --port 8000

dev-web:
	npm run dev --workspace=clients/web

dev-worker:
	cd backend && ../$(PYTHON) order_worker.py --daemon

build:
	npm run build --workspace=clients/web

test:
	$(PYTEST) -v

test-unit:
	$(PYTEST) backend/tests/unit/

test-integration:
	$(PYTEST) backend/tests/integration/

test-e2e:
	$(PYTEST) backend/tests/e2e/

test-playwright:
	npm run test:e2e --workspace=clients/web

test-cov:
	$(PYTEST) --cov=backend/src backend/tests/

prospects:
	cd backend && ../$(PYTHON) generate_prospects.py $(ARGS)

stats:
	cd backend && ../$(PYTHON) generate_prospects.py --stats

pilot:
	cd backend && ../$(PYTHON) scripts/generate_tinkko_pilot_batch.py

clean:
	rm -rf clients/web/dist .pytest_cache backend/.pytest_cache

