.PHONY: api worker compose-up

api:
	uvicorn trustai_api.main:create_app --factory --reload

worker:
	python -m trustai_worker.worker

compose-up:
	docker compose -f docker/docker-compose.yml up --build
