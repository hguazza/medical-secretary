.PHONY: install lint fmt typecheck test evals console console-text dev simulate check

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run pyright

test:
	uv run pytest

evals:
	uv run pytest -m evals -v

console:
	lk agent console

console-text:
	lk agent console --text

dev:
	lk agent dev

simulate:
	lk agent simulate text --scenarios scenarios.yaml

check: lint typecheck test
