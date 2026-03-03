.PHONY: up down logs test lint demo

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