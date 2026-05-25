.PHONY: install test coverage lint format typecheck check run

install:
	pip install -e ".[dev]"

test:
	pytest

coverage:
	pytest --cov=analyzer --cov=tantra --cov-report=term-missing --cov-fail-under=90

lint:
	ruff check analyzer tantra tests api.py

format:
	ruff format analyzer tantra tests api.py

typecheck:
	mypy analyzer

check: lint typecheck coverage

run:
	python api.py

run-prod:
	gunicorn "api:app" --workers 4 --bind 0.0.0.0:5000 --access-logfile - --error-logfile -
