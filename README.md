# Weather Analytics Pipeline

An end-to-end data pipeline that ingests hourly weather observations from the [Open-Meteo](https://open-meteo.com/) API, loads them into a PostgreSQL warehouse, and transforms them through a dbt staging → intermediate → mart → snapshot layer. An Airflow DAG orchestrates the full pipeline on a daily schedule.

## Architecture

```
Open-Meteo API
     │
     ▼
[Ingestion Service]       Python / psycopg2 — upserts into raw.weather_observations
     │
     ▼
[dbt – Staging]           stg_weather__observations       (incremental)
     │
     ▼
[dbt – Intermediate]      int_weather__daily_aggregates   (incremental)
     │
     ▼
[dbt – Mart]              mart_weather__city_stats        (full table)
     │
     ▼
[dbt – Snapshot]          city_stats_snapshot             (SCD Type 2)

All steps orchestrated daily by Apache Airflow (LocalExecutor).
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Ingestion | Python 3.11, Requests, psycopg2 |
| Warehouse | PostgreSQL 15 |
| Transformation | dbt-core 1.7, dbt-postgres |
| Orchestration | Apache Airflow 2.9 (LocalExecutor) |
| Containerisation | Docker, Docker Compose |
| CI | GitHub Actions |

---

## Prerequisites

- Docker + Docker Compose
- (optional) Python 3.11+ for running ingestion tests locally without Docker

---

## Quick Start — one-shot run

```bash
cp .env.example .env   # review / edit credentials if needed
make pipeline          # build images → ingest → dbt deps → dbt run → dbt snapshot
```

## Quick Start — scheduled Airflow

```bash
cp .env.example .env
make airflow           # starts warehouse + Airflow (webserver + scheduler)
```

Open **http://localhost:8080**, log in with the credentials printed in the container logs, and enable the `weather_pipeline` DAG. It runs daily and chains:

`ingest → dbt deps → dbt run → dbt snapshot → dbt test`

---

## Makefile Commands

| Command | What it does |
|---|---|
| `make up` | Start only the PostgreSQL warehouse |
| `make airflow` | Start warehouse + Airflow webserver/scheduler |
| `make pipeline` | Full one-shot run: warehouse → ingestion → dbt |
| `make ingest` | Run ingestion step only |
| `make transform` | Run `dbt deps` + `dbt run` |
| `make snapshot` | Run `dbt snapshot` |
| `make test` | Python unit tests + dbt schema tests |
| `make test-python` | Python unit tests (no DB required) |
| `make test-dbt` | dbt schema / data tests |
| `make logs` | Tail all container logs |
| `make down` | Stop all containers |
| `make clean` | Stop containers and wipe volumes |

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `WAREHOUSE_HOST` | `localhost` | PostgreSQL host |
| `WAREHOUSE_PORT` | `5432` | PostgreSQL port |
| `WAREHOUSE_USER` | `warehouse` | Database user |
| `WAREHOUSE_PASSWORD` | `warehouse` | Database password |
| `WAREHOUSE_DB` | `analytics` | Database name |
| `PAST_DAYS` | `7` | Days of historical data to fetch per run |

---

## Orchestration — Airflow DAG

**Location:** `orchestration/`

The `weather_pipeline` DAG runs on a `@daily` schedule with one retry per task (5-minute delay).

```
ingest ──► dbt_deps ──► dbt_run ──► dbt_snapshot ──► dbt_test
```

| Task | Type | What it does |
|---|---|---|
| `ingest` | PythonOperator | Fetches weather data and upserts into the raw table |
| `dbt_deps` | BashOperator | Installs dbt package dependencies |
| `dbt_run` | BashOperator | Runs all dbt models (incremental where applicable) |
| `dbt_snapshot` | BashOperator | Updates SCD Type 2 snapshot of city stats |
| `dbt_test` | BashOperator | Runs all dbt schema and data quality tests |

Airflow metadata is stored in a dedicated `airflow` database on the same PostgreSQL instance.

---

## Ingestion Service

**Location:** `ingestion/`

Fetches hourly weather data from the Open-Meteo forecast API for five cities and upserts into `raw.weather_observations`.

### Tracked Cities

| City | Latitude | Longitude |
|---|---|---|
| New York | 40.7128 | -74.0060 |
| London | 51.5074 | -0.1278 |
| Tokyo | 35.6762 | 139.6503 |
| Sydney | -33.8688 | 151.2093 |
| Mumbai | 19.0760 | 72.8777 |

Rows are upserted on `(city_name, observed_at)` — re-running ingestion is idempotent.

---

## dbt Transformation Layer

**Location:** `transform/`

Three-layer dbt project following the staging → intermediate → mart pattern, plus a snapshot layer for historical tracking.

### Layer 1 — Staging: `stg_weather__observations` *(incremental)*

**Input:** `raw.weather_observations`  
**Incremental key:** `ingested_at` — only processes rows ingested since the last run.

Cleans and types the raw data: renames `id` → `observation_id`, casts timestamps, coalesces nulls to `0.0`, and filters invalid rows.

### Layer 2 — Intermediate: `int_weather__daily_aggregates` *(incremental)*

**Input:** `stg_weather__observations`  
**Incremental key:** `(city_name, observation_date)` — recalculates the last 2 days to capture partial-day updates from the current run.

Collapses hourly readings into one row per city per day (avg/min/max temp, total precipitation, avg wind speed, reading count).

### Layer 3 — Mart: `mart_weather__city_stats` *(table)*

**Input:** `int_weather__daily_aggregates`

One summary row per city covering the full tracking window: lifetime temperature extremes, total precipitation, average conditions, and all-time temperature range.

### Layer 4 — Snapshot: `city_stats_snapshot` *(SCD Type 2)*

**Input:** `mart_weather__city_stats`  
**Strategy:** `check` on all columns.

Each time a city's aggregate stats change, dbt closes the previous record (`dbt_valid_to`) and inserts a new open record (`dbt_valid_from = now()`). This gives a full audit trail of how each city's metrics evolved over time — useful for answering questions like *"What was London's all-time max temp as of last Tuesday?"*

---

## Data Flow Summary

```
Open-Meteo API
       │
       ▼
raw.weather_observations   (hourly, upserted)
       │
       ▼  incremental on ingested_at
stg_weather__observations  (cleaned, typed)
       │
       ▼  incremental on (city_name, observation_date)
int_weather__daily_aggregates  (1 row / city / day)
       │
       ▼  full table rebuild
mart_weather__city_stats   (1 row / city, all-time stats)
       │
       ▼  SCD Type 2 snapshot
city_stats_snapshot        (full history of city stats changes)
```

---

## Project Structure

```
weather-analytics-pipeline/
├── ingestion/
│   ├── src/
│   │   ├── clients/open_meteo.py      # Open-Meteo API client
│   │   ├── loaders/warehouse.py       # PostgreSQL upsert loader
│   │   ├── pipelines/weather.py       # Orchestrates fetch → load
│   │   └── config.py                  # Config from env vars
│   └── tests/                         # Python unit tests
├── orchestration/
│   ├── dags/weather_pipeline.py       # Airflow DAG (daily schedule)
│   ├── Dockerfile                     # Airflow image with dbt + ingestion deps
│   └── requirements.txt
├── transform/
│   ├── models/
│   │   ├── staging/                   # stg_weather__observations (incremental)
│   │   ├── intermediate/              # int_weather__daily_aggregates (incremental)
│   │   └── marts/                     # mart_weather__city_stats (table)
│   └── snapshots/
│       └── city_stats_snapshot.sql    # SCD Type 2 history of city stats
├── .github/workflows/ci.yml           # CI: unit tests + full pipeline + dbt tests
├── docker-compose.yml
├── Makefile
└── .env.example
```
