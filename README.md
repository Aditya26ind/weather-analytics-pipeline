# Weather Analytics Pipeline

An end-to-end data pipeline that ingests hourly weather observations from the [Open-Meteo](https://open-meteo.com/) API, loads them into a PostgreSQL warehouse, and transforms them into analytics-ready tables using dbt.

## Architecture

```
Open-Meteo API
     │
     ▼
[Ingestion Service]  (Python / psycopg2)
     │  raw.weather_observations
     ▼
[dbt – Staging]      stg_weather__observations
     │
     ▼
[dbt – Intermediate] int_weather__daily_aggregates
     │
     ▼
[dbt – Mart]         mart_weather__city_stats
```

All services run in Docker. Orchestration order is enforced by `docker-compose` health-checks and service dependencies.

---

## Prerequisites

- Docker + Docker Compose
- (optional) Python 3.11+ for running ingestion tests locally without Docker

---

## Quick Start

```bash
cp .env.example .env          # review / edit credentials if needed
make pipeline                 # build images → ingest → dbt run
```

| Command | What it does |
|---|---|
| `make up` | Start only the PostgreSQL warehouse |
| `make pipeline` | Full run: warehouse → ingestion → dbt |
| `make ingest` | Run ingestion step only |
| `make transform` | Run `dbt run` only |
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
| `PAST_DAYS` | `7` | How many days of historical data to fetch per run |

---

## Ingestion Service

**Location:** `ingestion/`

Fetches hourly weather data from the Open-Meteo forecast API for five cities and upserts it into `raw.weather_observations`.

### Tracked Cities

| City | Latitude | Longitude |
|---|---|---|
| New York | 40.7128 | -74.0060 |
| London | 51.5074 | -0.1278 |
| Tokyo | 35.6762 | 139.6503 |
| Sydney | -33.8688 | 151.2093 |
| Mumbai | 19.0760 | 72.8777 |

### API Input

Calls `GET https://api.open-meteo.com/v1/forecast` with:

| Parameter | Value |
|---|---|
| `latitude` / `longitude` | City coordinates |
| `hourly` | `temperature_2m, precipitation, wind_speed_10m` |
| `past_days` | Value of `PAST_DAYS` env var (default `7`) |
| `forecast_days` | `1` |
| `timezone` | `UTC` |

### Raw Table Output — `raw.weather_observations`

| Column | Type | Description |
|---|---|---|
| `id` | `BIGSERIAL` | Surrogate primary key |
| `city_name` | `VARCHAR(100)` | City name |
| `latitude` | `DOUBLE PRECISION` | Latitude of the city |
| `longitude` | `DOUBLE PRECISION` | Longitude of the city |
| `observed_at` | `TIMESTAMP` | Observation timestamp (UTC) |
| `temperature_celsius` | `DOUBLE PRECISION` | Air temperature at 2 m |
| `precipitation_mm` | `DOUBLE PRECISION` | Precipitation amount |
| `wind_speed_kmh` | `DOUBLE PRECISION` | Wind speed at 10 m |
| `ingested_at` | `TIMESTAMP` | When the row was written (default `NOW()`) |

Rows are upserted on `(city_name, observed_at)` — re-running the ingestion is idempotent.

---

## dbt Transformation Layer

**Location:** `transform/`

Three-layer dbt project following the staging → intermediate → mart pattern.

### Layer 1 — Staging: `stg_weather__observations`

**Input:** `raw.weather_observations`

Cleans and types the raw data:
- Renames `id` → `observation_id`
- Casts `observed_at` to `TIMESTAMP`
- Coalesces `NULL` precipitation and wind values to `0.0`
- Filters out rows where `observed_at` or `temperature_celsius` is `NULL`

**Output columns:**

| Column | Type | Description |
|---|---|---|
| `observation_id` | `BIGINT` | Surrogate key (unique, not null) |
| `city_name` | `VARCHAR` | City name |
| `latitude` | `DOUBLE PRECISION` | City latitude |
| `longitude` | `DOUBLE PRECISION` | City longitude |
| `observed_at` | `TIMESTAMP` | Observation timestamp (UTC) |
| `temperature_celsius` | `DOUBLE PRECISION` | Temperature at 2 m |
| `precipitation_mm` | `DOUBLE PRECISION` | Precipitation (nulls replaced with 0) |
| `wind_speed_kmh` | `DOUBLE PRECISION` | Wind speed (nulls replaced with 0) |
| `ingested_at` | `TIMESTAMP` | Original ingestion timestamp |

---

### Layer 2 — Intermediate: `int_weather__daily_aggregates`

**Input:** `stg_weather__observations`

Collapses hourly readings into one row per city per day.

**Output columns:**

| Column | Type | Description |
|---|---|---|
| `city_name` | `VARCHAR` | City name |
| `observation_date` | `DATE` | Calendar date of the observations |
| `avg_temp_celsius` | `NUMERIC` | Average hourly temperature for the day |
| `max_temp_celsius` | `NUMERIC` | Highest hourly temperature for the day |
| `min_temp_celsius` | `NUMERIC` | Lowest hourly temperature for the day |
| `total_precipitation_mm` | `NUMERIC` | Total precipitation for the day |
| `avg_wind_speed_kmh` | `NUMERIC` | Average hourly wind speed for the day |
| `hourly_readings` | `BIGINT` | Count of hourly records that make up this day |

---

### Layer 3 — Mart: `mart_weather__city_stats`

**Input:** `int_weather__daily_aggregates`

Produces one summary row per city covering the full tracking window.

**Output columns:**

| Column | Type | Description |
|---|---|---|
| `city_name` | `VARCHAR` | City name (unique, not null) |
| `days_tracked` | `BIGINT` | Number of distinct calendar days with data |
| `tracking_start_date` | `DATE` | Earliest observation date |
| `tracking_end_date` | `DATE` | Most recent observation date |
| `avg_temp_celsius` | `NUMERIC` | Mean of daily average temperatures |
| `all_time_max_temp_celsius` | `NUMERIC` | Highest temperature ever recorded |
| `all_time_min_temp_celsius` | `NUMERIC` | Lowest temperature ever recorded |
| `total_precipitation_mm` | `NUMERIC` | Total precipitation across all tracked days |
| `avg_wind_speed_kmh` | `NUMERIC` | Mean of daily average wind speeds |
| `temp_range_celsius` | `NUMERIC` | All-time temperature range (max − min) |

Results are ordered alphabetically by `city_name`.

---

## Data Flow Summary

```
Open-Meteo API  ──►  raw.weather_observations  ──►  stg_weather__observations
                           (hourly rows)               (cleaned, typed)
                                                              │
                                                              ▼
                                              int_weather__daily_aggregates
                                                      (1 row / city / day)
                                                              │
                                                              ▼
                                                mart_weather__city_stats
                                                    (1 row / city, all-time)
```

---

## Project Structure

```
weather-analytics-pipeline/
├── ingestion/
│   ├── src/
│   │   ├── clients/open_meteo.py   # Open-Meteo API client
│   │   ├── loaders/warehouse.py    # PostgreSQL upsert loader
│   │   ├── pipelines/weather.py    # Orchestrates fetch → load
│   │   └── config.py               # Config from env vars
│   └── tests/                      # Python unit tests
├── transform/
│   └── models/
│       ├── staging/                # stg_weather__observations
│       ├── intermediate/           # int_weather__daily_aggregates
│       └── marts/                  # mart_weather__city_stats
├── docker-compose.yml
├── Makefile
└── .env.example
```
