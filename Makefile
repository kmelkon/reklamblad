# Makefile for Veckans Recept
# Provides convenient shortcuts for common development tasks

.PHONY: help
help: ## Show this help message
	@echo "Veckans Recept - Development Commands"
	@echo "======================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install Python and Node dependencies
	@echo "Installing Python dependencies..."
	pip install playwright requests
	playwright install chromium
	@echo ""
	@echo "Installing Node dependencies..."
	npm install
	@echo ""
	@echo "✓ Dependencies installed"

.PHONY: serve
serve: ## Start local development server
	@echo "Starting server at http://localhost:8000"
	@echo "Press Ctrl+C to stop"
	python -m http.server 8000

.PHONY: scrape
scrape: ## Run scrapers (deals + match recipes)
	@echo "Scraping deals..."
	python scrape_deals.py
	@echo ""
	@echo "Matching recipes..."
	python match_recipes.py
	@echo ""
	@echo "✓ Scraping complete"

.PHONY: scrape-deals
scrape-deals: ## Scrape deals only
	python scrape_deals.py

.PHONY: match
match: ## Match recipes to deals
	python match_recipes.py

.PHONY: test
test: ## Run unit tests
	@echo "Running unit tests..."
	python test_match_recipes.py
	@echo ""
	@echo "✓ Tests complete"

.PHONY: validate
validate: ## Validate JSON data files
	@echo "Validating data files..."
	python validate_data.py

.PHONY: optimize
optimize: ## Optimize recipe_matches.json file size
	@echo "Optimizing data files..."
	python optimize_data.py

.PHONY: monitor
monitor: ## Show data quality metrics
	python monitor.py

.PHONY: lint
lint: ## Run all linters
	@echo "Running ESLint..."
	npm run lint:js
	@echo ""
	@echo "Running Stylelint..."
	npm run lint:css
	@echo ""
	@echo "✓ Linting complete"

.PHONY: lint-fix
lint-fix: ## Run linters and auto-fix issues
	@echo "Auto-fixing lint issues..."
	npm run lint:fix
	@echo "✓ Auto-fix complete"

.PHONY: typecheck
typecheck: ## Run TypeScript type checking
	@echo "Running TypeScript type checking..."
	npm run typecheck
	@echo "✓ Type checking complete"

.PHONY: check
check: test lint typecheck validate ## Run all checks (tests, lints, validation)
	@echo ""
	@echo "✓ All checks passed"

.PHONY: clean
clean: ## Clean generated and temporary files
	@echo "Cleaning generated files..."
	rm -f *_optimized.json *_optimized_debug.json
	rm -rf __pycache__ *.pyc *.pyo
	rm -rf .pytest_cache .coverage htmlcov
	@echo "✓ Cleanup complete"

.PHONY: status
status: ## Show git status and file sizes
	@echo "Git Status:"
	@echo "==========="
	@git status -s
	@echo ""
	@echo "Data File Sizes:"
	@echo "================"
	@ls -lh deals.json recipes.json recipe_matches.json 2>/dev/null | awk '{print $$9 " - " $$5}' || echo "No data files found"

.PHONY: update
update: scrape validate ## Scrape, validate, and prepare for commit
	@echo ""
	@echo "✓ Data updated and validated"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review changes: git diff"
	@echo "  2. Commit: git add . && git commit -m 'Update deals'"
	@echo "  3. Push: git push"

.PHONY: dev
dev: install test lint serve ## Full dev setup: install, test, lint, serve

.PHONY: ci
ci: test lint typecheck validate ## Run all CI checks locally
	@echo ""
	@echo "✓ All CI checks passed"

.PHONY: stats
stats: monitor ## Alias for monitor

# Default target
.DEFAULT_GOAL := help
