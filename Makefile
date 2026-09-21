.PHONY: install dev backend frontend test lint format demo docker-up docker-down

install:
	python -m pip install -e "./backend[dev]"
	cd frontend && npm ci

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest --cov=app --cov-report=term-missing
	cd frontend && npm run build

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd backend && ruff check --fix .

demo:
	python scripts/seed_demo.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down
