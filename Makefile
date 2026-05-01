.PHONY: setup build dev sandbox

build:
	@echo "Building application Docker image..."
	docker build -t quartz:latest .
	@echo "Starting MongoDB and RabbitMQ..."
	docker compose up -d

dev:
	@echo "Running development server: uvicorn main:app --reload --port 8000"
	set -a && . .env && set +a && . .venv/bin/activate && uvicorn main:app --reload --port 8000

setup:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip && python -V
	@echo "Building Docker image..."
	docker build -t quartz:latest .
	@echo "Running container..."
	docker compose up -d

sandbox:
	@echo "Building Docker image from sandbox.Dockerfile..."
	docker build -f sandbox/sandbox.Dockerfile -t quartz-sandbox:latest sandbox
