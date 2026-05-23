.PHONY: help up down pipeline ingest transform test test-python test-dbt logs clean

help:
	@echo "Commands:"
	@echo "  make up           start the PostgreSQL warehouse"
	@echo "  make pipeline     run full ingestion + dbt pipeline"
	@echo "  make ingest       run ingestion only"
	@echo "  make transform    run dbt run only"
	@echo "  make test         run all tests (Python unit + dbt)"
	@echo "  make test-python  run Python unit tests only (no DB needed)"
	@echo "  make test-dbt     run dbt tests only"
	@echo "  make logs         tail all service logs"
	@echo "  make down         stop all containers"
	@echo "  make clean        stop containers and wipe volumes"

up:
	docker compose up -d postgres

down:
	docker compose down

pipeline:
	docker compose up --build

ingest:
	docker compose up -d postgres
	docker compose run --rm --build ingestion

transform:
	docker compose up -d postgres
	docker compose run --rm --build -e DBT_PROFILES_DIR=/dbt dbt run

test: test-python test-dbt

test-python:
	docker compose run --rm --build test-ingestion

test-dbt:
	docker compose up -d postgres
	docker compose run --rm -e DBT_PROFILES_DIR=/dbt dbt test

logs:
	docker compose logs -f

clean:
	docker compose down -v
