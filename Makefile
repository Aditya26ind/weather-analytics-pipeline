.PHONY: help up down airflow pipeline ingest transform snapshot test test-python test-dbt logs clean

help:
	@echo "Commands:"
	@echo "  make up           start the PostgreSQL warehouse"
	@echo "  make airflow      start Airflow scheduler + webserver (http://localhost:8080)"
	@echo "  make pipeline     run full ingestion + dbt pipeline (one-shot)"
	@echo "  make ingest       run ingestion only"
	@echo "  make transform    run dbt run only"
	@echo "  make snapshot     run dbt snapshot only"
	@echo "  make test         run all tests (Python unit + dbt)"
	@echo "  make test-python  run Python unit tests only (no DB needed)"
	@echo "  make test-dbt     run dbt tests only"
	@echo "  make logs         tail all service logs"
	@echo "  make down         stop all containers"
	@echo "  make clean        stop containers and wipe volumes"

up:
	docker compose up -d postgres

airflow:
	docker compose up -d postgres
	docker compose up --build airflow

down:
	docker compose down

pipeline:
	docker compose up --build

ingest:
	docker compose up -d postgres
	docker compose run --rm --build ingestion

transform:
	docker compose up -d postgres
	docker compose run --rm --build -e DBT_PROFILES_DIR=/dbt dbt deps
	docker compose run --rm -e DBT_PROFILES_DIR=/dbt dbt run

snapshot:
	docker compose up -d postgres
	docker compose run --rm -e DBT_PROFILES_DIR=/dbt dbt snapshot

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
