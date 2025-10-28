.PHONY: help install install-dev check format lint typecheck test clean

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  check          Run all checks (format, lint, typecheck, test)"
	@echo "  format         Format code with black"
	@echo "  lint           Run ruff linter"
	@echo "  typecheck      Run mypy type checker"
	@echo "  test           Run pytest tests (verbose)"
	@echo "  test-v         Run pytest tests with extra verbose output"
	@echo "  test-quiet     Run pytest tests quietly"
	@echo "  clean          Clean up generated files"

install: ## Install production dependencies
	uv sync --no-dev

install-dev: ## Install all dependencies including dev
	uv sync

format: ## Format code with black
	uv run black src/ tests/

lint: ## Run ruff linter
	uv run ruff check src/ tests/

typecheck: ## Run mypy type checker
	uv run mypy src/

test: ## Run pytest tests
	uv run pytest tests/ -v -s

test-v: ## Run pytest tests with extra verbose output
	uv run pytest tests/ -vv -s --tb=short

test-quiet: ## Run pytest tests quietly
	uv run pytest tests/ -q

check: format lint typecheck test ## Run all checks

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true

