# Makefile for Trustworthy RAG System
# Convenient commands for development and deployment

.PHONY: help install test lint format clean run run-api docker-build docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install dependencies including development tools
	pip install -r requirements.txt

test: ## Run all tests
	pytest

test-verbose: ## Run tests with verbose output
	pytest -v

test-coverage: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term

test-unit: ## Run only unit tests
	pytest -m unit

test-integration: ## Run only integration tests
	pytest -m integration

lint: ## Run linting checks
	flake8 src tests
	mypy src --ignore-missing-imports

format: ## Format code with black
	black src tests

format-check: ## Check code formatting
	black src tests --check

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf logs/*.log
	rm -f interaction_logs.json

run: ## Run the CLI application
	cd src && python app.py

run-api: ## Run the FastAPI server
	cd src && python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000

run-api-prod: ## Run the API in production mode
	cd src && python -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4

index-pinecone: ## Index documents to Pinecone (standard set)
	cd scripts && python index_to_pinecone.py

index-pinecone-expanded: ## Index expanded documents to Pinecone
	cd scripts && python index_to_pinecone.py --expanded

docker-build: ## Build Docker image
	docker build -t trustworthy-rag:latest .

docker-up: ## Start Docker Compose services
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-shell: ## Get shell access to RAG container
	docker-compose exec rag-api /bin/bash

check: lint test ## Run all checks (lint + test)

setup: install ## Initial setup
	@echo "✅ Setup complete! Run 'make help' to see available commands."

api-docs: ## Open API documentation in browser
	@echo "Starting API server and opening docs..."
	@echo "Visit: http://localhost:8000/docs"

metrics: ## View Prometheus metrics
	@echo "Visit: http://localhost:9090"

grafana: ## Open Grafana dashboard
	@echo "Visit: http://localhost:3000 (admin/admin)"

# Development workflow
dev: clean install run ## Clean, install, and run development server

# CI/CD targets
ci: lint test ## Run CI checks

deploy-prep: clean test docker-build ## Prepare for deployment

.DEFAULT_GOAL := help

