.PHONY: api worker compose-up install test lint typecheck smoke

install:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

lint:
	ruff check .

typecheck:
	mypy

smoke:
	./scripts/smoke_week4.sh

api:
	uvicorn trustai_api.main:create_app --factory --reload

worker:
	python -m trustai_worker.worker

compose-up:
	docker compose -f docker/docker-compose.yml up --build
