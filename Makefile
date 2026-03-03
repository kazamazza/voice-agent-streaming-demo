.PHONY: nlp-demo up down logs test lint demo data parquet train

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

train:
	python scripts/train_intent_model.py

nlp-demo:
	python scripts/train_intent_model.py
	python scripts/demo_intent_inference.py