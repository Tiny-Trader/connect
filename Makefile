SHELL := /bin/sh

.PHONY: lint typecheck test test-fast coverage precommit-install precommit-run ci

lint:
	poetry run ruff check .

typecheck:
	poetry run mypy tt_connect/

test:
	poetry run pytest

test-fast:
	poetry run pytest -q tests/unit tests/integration

coverage:
	poetry run pytest tests/unit tests/integration --cov=tt_connect --cov-report=xml --cov-fail-under=64

precommit-install:
	pre-commit install --hook-type pre-commit --hook-type pre-push

precommit-run:
	pre-commit run --all-files

ci: lint typecheck test-fast coverage
