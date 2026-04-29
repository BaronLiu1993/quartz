.PHONY: setup build sandbox

build:
	. .venv/bin/activate && uvicorn main:app --reload --port 8000

setup:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip && python -V
	@echo "Building Docker image..."
	docker build -t quartz:latest .
	@echo "Running container..."
	docker run -d --name quartz -p 27017:27017 quartz:latest

sandbox:
	@echo "Building Docker image from sandbox.Dockerfile..."
	docker build -f sandbox/sandbox.Dockerfile -t quartz-sandbox:latest sandbox
