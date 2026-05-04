.PHONY: setup build dev worker sandbox

setup:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements.txt
	@echo "Starting MongoDB and RabbitMQ..."
	docker compose up -d --build

build:
	@echo "Starting MongoDB and RabbitMQ containers..."
	docker compose up -d --build

dev:
	@echo "Running development server: uvicorn main:app --reload --port 8000"
	set -a && . .env && set +a && . .venv/bin/activate && uvicorn main:app --reload --port 8000

worker:
	@echo "Running Celery worker: celery -A async_queue.config worker -Q pr --loglevel=info"
	set -a && . .env && set +a && . .venv/bin/activate && celery -A async_queue.config worker -Q pr --loglevel=info

sandbox:
	@echo "Building Docker image from sandbox.Dockerfile..."
	docker build -f sandbox/sandbox.Dockerfile -t quartz-sandbox:latest sandbox
