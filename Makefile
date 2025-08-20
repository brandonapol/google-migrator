# Variables
VENV_NAME := venv
PYTHON := python3
PIP := $(VENV_NAME)/bin/pip
PYTHON_VENV := $(VENV_NAME)/bin/python
UVICORN := $(VENV_NAME)/bin/uvicorn

# Default target
.PHONY: help
help:
	@echo "Google Drive Backup Service"
	@echo ""
	@echo "Available commands:"
	@echo "  setup       - Create virtual environment and install dependencies"
	@echo "  install     - Install/update dependencies"
	@echo "  run         - Run the development server (with auto-reload)"
	@echo "  run-stable  - Run server without auto-reload (more stable)"
	@echo "  prod        - Run production server"
	@echo "  clean       - Clean up generated files"
	@echo "  test        - Run tests"
	@echo "  format      - Format code with black"
	@echo "  lint        - Run linting"
	@echo ""
	@echo "File locations:"
	@echo "  Downloads: $(PWD)/downloads/"
	@echo "  Config:    $(PWD)/.env"
	@echo ""
	@echo "Setup instructions:"
	@echo "1. Set environment variables in .env file:"
	@echo "   GOOGLE_CLIENT_ID=your_client_id"
	@echo "   GOOGLE_CLIENT_SECRET=your_client_secret"
	@echo "   REDIRECT_URL=http://localhost:8000/auth/callback"
	@echo "2. Run 'make setup' to install dependencies"
	@echo "3. Run 'make run-stable' to start the server"

# Create virtual environment
$(VENV_NAME):
	$(PYTHON) -m venv $(VENV_NAME)
	$(PIP) install --upgrade pip

# Install dependencies
.PHONY: install
install: $(VENV_NAME)
	$(PIP) install fastapi[all]==0.104.1
	$(PIP) install uvicorn[standard]==0.24.0
	$(PIP) install google-auth==2.23.4
	$(PIP) install google-auth-oauthlib==1.1.0
	$(PIP) install google-api-python-client==2.108.0
	$(PIP) install python-multipart==0.0.6
	$(PIP) install jinja2==3.1.2
	$(PIP) install aiofiles==23.2.0
	$(PIP) install python-dotenv==1.0.0

# Setup everything from scratch
.PHONY: setup
setup: clean install
	@echo "Creating directories..."
	mkdir -p templates downloads
	@echo "Creating sample .env file..."
	@if [ ! -f .env ]; then \
		echo "GOOGLE_CLIENT_ID=your_client_id_here" > .env; \
		echo "GOOGLE_CLIENT_SECRET=your_client_secret_here" >> .env; \
		echo "REDIRECT_URL=http://localhost:8000/auth/callback" >> .env; \
		echo "Created .env file - please update with your Google OAuth credentials"; \
	fi
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Update .env with your Google OAuth credentials"
	@echo "2. Run 'make run' to start the server"

# Run development server
.PHONY: run
run: $(VENV_NAME)
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "🚀 Starting server at http://localhost:8000"
	@echo "📁 Downloads will be saved to: $(PWD)/downloads/"
	$(UVICORN) app:app --reload --host 0.0.0.0 --port 8000 --reload-exclude="venv/*"

# Run without auto-reload (more stable)
.PHONY: run-stable
run-stable: $(VENV_NAME)
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "🚀 Starting stable server at http://localhost:8000"
	@echo "📁 Downloads will be saved to: $(PWD)/downloads/"
	$(UVICORN) app:app --host 0.0.0.0 --port 8000

# Run production server
.PHONY: prod
prod: $(VENV_NAME)
	$(UVICORN) app:app --host 0.0.0.0 --port 8000 --workers 4

# Development tools
.PHONY: format
format: $(VENV_NAME)
	$(PIP) install black
	$(VENV_NAME)/bin/black *.py

.PHONY: lint
lint: $(VENV_NAME)
	$(PIP) install flake8
	$(VENV_NAME)/bin/flake8 *.py

.PHONY: test
test: $(VENV_NAME)
	$(PIP) install pytest
	$(VENV_NAME)/bin/pytest tests/

# Clean up
.PHONY: clean
clean:
	rm -rf $(VENV_NAME)
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf downloads/*
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Docker support
.PHONY: docker-build
docker-build:
	docker build -t drive-backup .

.PHONY: docker-run
docker-run:
	docker run -p 8000:8000 --env-file .env drive-backup

# Check requirements
.PHONY: check-env
check-env:
	@echo "Checking environment variables..."
	@if [ -z "$$GOOGLE_CLIENT_ID" ]; then echo "❌ GOOGLE_CLIENT_ID not set"; else echo "✅ GOOGLE_CLIENT_ID set"; fi
	@if [ -z "$$GOOGLE_CLIENT_SECRET" ]; then echo "❌ GOOGLE_CLIENT_SECRET not set"; else echo "✅ GOOGLE_CLIENT_SECRET set"; fi
	@if [ -z "$$REDIRECT_URL" ]; then echo "❌ REDIRECT_URL not set"; else echo "✅ REDIRECT_URL set"; fi

# Show logs
.PHONY: logs
logs:
	tail -f logs/app.log

# Install dev dependencies
.PHONY: dev-install
dev-install: install
	$(PIP) install black flake8 pytest

.PHONY: requirements
requirements: $(VENV_NAME)
	$(PIP) freeze > requirements.txt
	@echo "Requirements saved to requirements.txt"
