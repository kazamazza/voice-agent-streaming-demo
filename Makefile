.PHONY: up down logs test lint demo data parquet

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

test:
	pip install -e ".[dev]"
	pytest -q

lint:
	pip install -e ".[dev]"
	ruff check .

demo:
	python tools/call_simulator.py

data:
	python scripts/generate_synthetic_logs.py

parquet:
	python scripts/build_dataset_parquet.py