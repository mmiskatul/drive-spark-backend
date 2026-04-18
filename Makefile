.PHONY: install install-dev seed-admin dev lint test docker-build docker-up

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

seed-admin:
	python -m app.scripts.seed_admin

dev:
	python -m app.scripts.seed_admin
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check .

test:
	pytest

docker-build:
	docker build -t drive-spark-rent-api .

docker-up:
	docker compose up --build
