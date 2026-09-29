.PHONY: help build deploy clean test validate install lint format security-scan

# Default target
help:
	@echo "PowerScale Cluster Monitor - Available Commands"
	@echo ""
	@echo "Build Commands:"
	@echo "  make build          - Build Lambda deployment package"
	@echo "  make clean          - Clean build artifacts"
	@echo ""
	@echo "Deployment Commands:"
	@echo "  make deploy         - Deploy to AWS (requires AWS credentials)"
	@echo "  make validate       - Validate Terraform configuration"
	@echo ""
	@echo "Development Commands:"
	@echo "  make install        - Install Python dependencies"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linting"
	@echo "  make format         - Format code"
	@echo "  make security-scan  - Run security scan"
	@echo ""
	@echo "Local CLI:"
	@echo "  make run-local      - Run local CLI monitor"

# Detect OS
OS := $(shell uname -s 2>/dev/null || echo Windows)

# Build Lambda deployment package
build:
	@echo "Building Lambda deployment package..."
	@cd powerscale-monitor/aws && \
	if [ "$(OS)" = "Linux" ] || [ "$(OS)" = "Darwin" ]; then \
		chmod +x build.sh && ./build.sh; \
	else \
		powershell.exe -ExecutionPolicy Bypass -File build.ps1; \
	fi

# Deploy to AWS
deploy: build
	@echo "Deploying to AWS..."
	@cd powerscale-monitor/aws && \
	if [ "$(OS)" = "Linux" ] || [ "$(OS)" = "Darwin" ]; then \
		chmod +x deploy.sh && ./deploy.sh; \
	else \
		powershell.exe -ExecutionPolicy Bypass -File deploy.ps1; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@cd powerscale-monitor/aws && \
	rm -rf package deployment.zip 2>/dev/null || \
	powershell.exe -Command "Remove-Item -Recurse -Force package, deployment.zip -ErrorAction SilentlyContinue"

# Validate Terraform configuration
validate:
	@echo "Validating Terraform configuration..."
	@cd powerscale-monitor/aws/terraform && \
	terraform init -backend=false && \
	terraform validate

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	@pip install -r powerscale-monitor/requirements.txt
	@pip install -r powerscale-monitor/aws/aws-requirements.txt

# Run tests
test:
	@echo "Running tests..."
	@cd powerscale-monitor/aws && python -m pytest tests/ -v

# Run linting
lint:
	@echo "Running linting..."
	@python -m flake8 powerscale-monitor/ --max-line-length=100 --exclude=.git,__pycache__,.venv
	@python -m pylint powerscale-monitor/ --disable=C0114,C0115,C0116

# Format code
format:
	@echo "Formatting code..."
	@python -m black powerscale-monitor/ --line-length=100
	@python -m isort powerscale-monitor/

# Security scan
security-scan:
	@echo "Running security scan..."
	@pip install bandit safety
	@bandit -r powerscale-monitor/ -f json -o security-report.json
	@safety check -r powerscale-monitor/requirements.txt

# Run local CLI monitor
run-local:
	@echo "Running local CLI monitor..."
	@cd powerscale-monitor && python powerscale_cluster_monitor.py

# Terraform plan
plan:
	@echo "Running Terraform plan..."
	@cd powerscale-monitor/aws/terraform && terraform plan

# Terraform apply
apply:
	@echo "Running Terraform apply..."
	@cd powerscale-monitor/aws/terraform && terraform apply

# Terraform destroy
destroy:
	@echo "Running Terraform destroy..."
	@cd powerscale-monitor/aws/terraform && terraform destroy
