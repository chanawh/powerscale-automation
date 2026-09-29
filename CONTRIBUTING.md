# Contributing to PowerScale Cluster Monitor

Thank you for your interest in contributing! This document provides guidelines for contributing to the PowerScale Cluster Monitor project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Project Structure](#project-structure)

## Code of Conduct

This project adheres to a code of conduct that all contributors must follow:

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- AWS CLI (for AWS deployment testing)
- Terraform 1.5.7+ (for infrastructure testing)
- Make (optional, for convenience)

### Setup Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/powerscale-automation.git
   cd powerscale-automation
   ```

3. Install dependencies:
   ```bash
   make install
   # or
   pip install -r powerscale-monitor/requirements.txt
   pip install -r powerscale-monitor/aws/aws-requirements.txt
   ```

4. Install development tools:
   ```bash
   pip install pytest flake8 black isort pylint mypy
   ```

## Development Workflow

### 1. Create a Branch

Create a new branch for your contribution:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or changes

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards outlined below
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

Run the test suite:
```bash
make test
# or
cd powerscale-monitor/aws
python -m pytest tests/ -v
```

Run linting:
```bash
make lint
# or
flake8 powerscale-monitor/ --max-line-length=100
black powerscale-monitor/ --check
isort powerscale-monitor/ --check-only
```

Validate Terraform:
```bash
make validate
# or
cd powerscale-monitor/aws/terraform
terraform init -backend=false
terraform validate
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:
```bash
git add .
git commit -m "feat: add support for custom metrics"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Maintenance tasks

### 5. Push and Create Pull Request

Push your branch:
```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:
- Clear title and description
- Reference any related issues
- Screenshots for UI changes (if applicable)
- Testing instructions

## Coding Standards

### Python Code Style

We follow PEP 8 with some modifications:

- Line length: 100 characters (instead of 79)
- Use type hints for all function signatures
- Use docstrings for all functions and classes
- Use meaningful variable and function names

Example:
```python
from typing import Dict, List, Optional

def calculate_health_score(
    events: List[Dict[str, any]],
    critical_threshold: int = 50,
    degraded_threshold: int = 80
) -> tuple[int, str]:
    """
    Calculate health score based on events.
    
    Args:
        events: List of event dictionaries
        critical_threshold: Score threshold for critical status
        degraded_threshold: Score threshold for degraded status
        
    Returns:
        Tuple of (health_score, status)
    """
    score = 100
    for event in events:
        if event.get('severity') == 'critical':
            score -= 20
    return max(0, score), 'HEALTHY' if score >= 80 else 'DEGRADED'
```

### Terraform Style

Follow Terraform best practices:

- Use consistent naming conventions
- Add descriptions to all variables and outputs
- Use `terraform fmt` to format code
- Use modules for reusable components

Example:
```hcl
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

resource "aws_lambda_function" "monitor" {
  function_name = "powerscale-monitor"
  description   = "Monitors PowerScale cluster health"
  # ...
}
```

### Shell Scripts

- Use `set -e` for error handling
- Add comments for complex operations
- Use meaningful variable names
- Quote variables to prevent word splitting

Example:
```bash
#!/bin/bash
set -e

# Build Lambda deployment package
echo "Building deployment package..."
./build.sh

# Validate Terraform configuration
echo "Validating Terraform..."
terraform validate
```

## Testing

### Unit Tests

Write unit tests for new functionality:

```python
# tests/test_health_score.py
import pytest
from powerscale_monitor import calculate_health_score

def test_health_score_critical_events():
    events = [
        {'severity': 'critical', 'causes': ['Disk failure']},
        {'severity': 'warning', 'causes': ['High CPU']}
    ]
    score, status = calculate_health_score(events)
    assert score == 75  # 100 - 20 - 5
    assert status == 'DEGRADED'
```

### Integration Tests

Test integration with external services:

```python
def test_lambda_invocation():
    response = lambda_handler({}, None)
    assert response['statusCode'] == 200
```

### Test Coverage

Maintain test coverage above 80%:
```bash
pip install pytest-cov
pytest --cov=powerscale_monitor --cov-report=html
```

## Documentation

### Code Documentation

- Add docstrings to all functions and classes
- Use Google or NumPy style docstrings
- Include type hints in docstrings

### README Updates

Update README.md for:
- New features
- Configuration changes
- Breaking changes
- New dependencies

### Architecture Documentation

Update docs/ARCHITECTURE.md for:
- New components
- Architecture changes
- Data flow changes

## Submitting Changes

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] PR description explains the change
- [ ] No breaking changes without discussion

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Project Structure

```
powerscale-automation/
├── .github/
│   └── workflows/
│       ├── validate.yml    # CI/CD validation
│       └── deploy.yml      # CI/CD deployment
├── docs/
│   ├── ARCHITECTURE.md     # Architecture documentation
│   └── screenshots/        # Screenshots and diagrams
├── powerscale-monitor/
│   ├── aws/
│   │   ├── build.sh        # Linux/Mac build script
│   │   ├── build.ps1       # Windows build script
│   │   ├── deploy.sh       # Linux/Mac deploy script
│   │   ├── deploy.ps1      # Windows deploy script
│   │   ├── lambda_function.py
│   │   ├── terraform/      # Infrastructure code
│   │   └── tests/          # Unit tests
│   ├── powerscale_cluster_monitor.py
│   ├── requirements.txt
│   └── README.md
├── Makefile                # Unified commands
├── CONTRIBUTING.md         # This file
├── LICENSE
└── README.md
```

## Getting Help

If you need help:

- Check existing issues and discussions
- Read the documentation in docs/
- Ask questions in GitHub Discussions
- Contact maintainers via GitHub issues

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing! 🎉
