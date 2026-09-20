.PHONY: help sync lint format typecheck test test-fast check smoke serve fixtures data-card audit clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

sync: ## install dev environment
	uv sync --extra dev

lint: ## ruff check + format check
	uv run ruff check src tests examples scripts
	uv run ruff format --check src tests examples scripts

format: ## apply ruff formatting and safe fixes
	uv run ruff check --fix src tests examples scripts
	uv run ruff format src tests examples scripts

typecheck: ## mypy --strict on the package
	uv run mypy src/forecheck

test: ## full offline test suite
	uv run pytest -q

test-fast: ## skip slow tests
	uv run pytest -q -m "not slow"

check: lint typecheck test ## everything CI runs

smoke: ## end-to-end offline smoke: fixtures -> mock scores -> calibrate -> evaluate -> policy -> API
	uv run python scripts/smoke_offline.py

fixtures: ## regenerate the committed offline fixture dataset
	uv run forecheck data generate --offline --config configs/data/fixtures.yaml --out data/fixtures
	uv run forecheck data split data/fixtures

data-card: ## regenerate docs/data-card.md from the fixture manifests and code catalogues
	uv run python scripts/gen_data_card.py

serve: ## run the API against the mock backend
	uv run forecheck serve --backend mock

audit: ## dependency vulnerability scan
	uv run pip-audit

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov coverage.xml dist build
