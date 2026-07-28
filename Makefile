.PHONY: install test lint init-db
install:
	python -m pip install -e ".[dev]"
test:
	python -m pytest
lint:
	python -m ruff check src tests
init-db:
	python -m dengue_rj.cli build-database
