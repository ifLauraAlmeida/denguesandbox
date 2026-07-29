.PHONY: install test lint audit init-db
install:
	python -m pip install -e ".[dev]"
test:
	python -m pytest
lint:
	python -m ruff check src tests
audit:
	python -m dengue_rj.cli audit-release
init-db:
	python -m dengue_rj.cli build-database
