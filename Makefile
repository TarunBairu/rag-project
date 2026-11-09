.PHONY: help install run test lint clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       Install python requirements"
	@echo "  make run           Start FastAPI dev server with auto-reload"
	@echo "  make test          Run pytest suite"
	@echo "  make lint          Lint codebase with flake8"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-up     Start multi-container app & postgres via docker-compose"
	@echo "  make docker-down   Stop and tear down docker containers"
	@echo "  make clean         Remove cache files and temporary artifacts"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

run:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

test:
	python -m pytest tests/ -v

lint:
	flake8 . --count --max-line-length=127 --statistics

docker-build:
	docker build -f docker/Dockerfile -t rag-app:latest .

docker-up:
	docker compose -f docker/docker-compose.yml up --build -d

docker-down:
	docker compose -f docker/docker-compose.yml down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov
