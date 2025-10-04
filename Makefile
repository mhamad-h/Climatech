.PHONY: help install dev test lint clean build docker-build docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install all dependencies (backend + frontend)"
	@echo "  dev         - Run development servers concurrently"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run linters and formatters"
	@echo "  clean       - Clean generated files and caches"
	@echo "  build       - Build production artifacts"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up   - Start Docker containers"
	@echo "  docker-down - Stop Docker containers"
	@echo "  train       - Train ML models"
	@echo "  data        - Download and prepare data"

# Install dependencies
install: install-backend install-frontend

install-backend:
	cd backend && python -m venv venv && \
	. venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

install-frontend:
	cd client && npm install

# Development
dev:
	@echo "Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "Docs: http://localhost:8000/docs"
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && \
	. venv/bin/activate && \
	python app.py

dev-frontend:
	cd client && npm run dev

# Testing
test: test-backend test-frontend

test-backend:
	cd backend && \
	. venv/bin/activate && \
	pytest tests/ -v --cov=. --cov-report=html

test-frontend:
	cd client && npm test -- --coverage

# Linting and formatting
lint: lint-backend lint-frontend

lint-backend:
	cd backend && \
	. venv/bin/activate && \
	black . && \
	flake8 . && \
	isort .

lint-frontend:
	cd client && \
	npm run lint && \
	npm run format

# Cleaning
clean:
	rm -rf backend/venv/
	rm -rf backend/__pycache__/
	rm -rf backend/.pytest_cache/
	rm -rf backend/htmlcov/
	rm -rf client/node_modules/
	rm -rf client/dist/
	rm -rf client/.coverage/
	rm -rf data/cache/
	rm -rf logs/

# Building
build: build-backend build-frontend

build-backend:
	cd backend && \
	. venv/bin/activate && \
	python -m build

build-frontend:
	cd client && npm run build

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started:"
	@echo "  Backend: http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"

docker-down:
	docker-compose down

# ML Pipeline
train:
	cd ml && \
	python download_data.py && \
	python build_dataset.py && \
	python train.py && \
	python evaluate.py

data:
	cd ml && python download_data.py

# Setup for new contributors
setup: install
	cp .env.example .env
	mkdir -p data/cache logs
	@echo "Setup complete! Run 'make dev' to start development."

# Production deployment
deploy:
	docker-compose -f docker-compose.prod.yml up -d

# Health check
health:
	@curl -s http://localhost:8000/health || echo "Backend not responding"
	@curl -s http://localhost:5173 || echo "Frontend not responding"