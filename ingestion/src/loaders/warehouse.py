from typing import List

import psycopg2
from psycopg2.extras import execute_values

from ..clients.open_meteo import WeatherObservation
from ..config import Config
from ..logger import get_logger

logger = get_logger(__name__)

_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS raw;"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS raw.weather_observations (
    id                   BIGSERIAL PRIMARY KEY,
    city_name            VARCHAR(100)     NOT NULL,
    latitude             DOUBLE PRECISION NOT NULL,
    longitude            DOUBLE PRECISION NOT NULL,
    observed_at          TIMESTAMP        NOT NULL,
    temperature_celsius  DOUBLE PRECISION,
    apparent_temperature DOUBLE PRECISION,
    relative_humidity_pct DOUBLE PRECISION,
    precipitation_mm     DOUBLE PRECISION,
    wind_speed_kmh       DOUBLE PRECISION,
    ingested_at          TIMESTAMP        DEFAULT NOW(),
    UNIQUE (city_name, observed_at)
);
"""

_ADD_COLUMNS = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'raw' AND table_name = 'weather_observations'
          AND column_name = 'apparent_temperature'
    ) THEN
        ALTER TABLE raw.weather_observations ADD COLUMN apparent_temperature DOUBLE PRECISION;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'raw' AND table_name = 'weather_observations'
          AND column_name = 'relative_humidity_pct'
    ) THEN
        ALTER TABLE raw.weather_observations ADD COLUMN relative_humidity_pct DOUBLE PRECISION;
    END IF;
END$$;
"""

_UPSERT = """
INSERT INTO raw.weather_observations
    (city_name, latitude, longitude, observed_at,
     temperature_celsius, apparent_temperature, relative_humidity_pct,
     precipitation_mm, wind_speed_kmh)
VALUES %s
ON CONFLICT (city_name, observed_at) DO UPDATE SET
    temperature_celsius   = EXCLUDED.temperature_celsius,
    apparent_temperature  = EXCLUDED.apparent_temperature,
    relative_humidity_pct = EXCLUDED.relative_humidity_pct,
    precipitation_mm      = EXCLUDED.precipitation_mm,
    wind_speed_kmh        = EXCLUDED.wind_speed_kmh,
    ingested_at           = NOW();
"""


class WarehouseLoader:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._conn = None

    def connect(self) -> None:
        logger.info(
            "Connecting to warehouse at %s:%d/%s",
            self._config.warehouse_host,
            self._config.warehouse_port,
            self._config.warehouse_db,
        )
        self._conn = psycopg2.connect(
            host=self._config.warehouse_host,
            port=self._config.warehouse_port,
            user=self._config.warehouse_user,
            password=self._config.warehouse_password,
            dbname=self._config.warehouse_db,
        )
        logger.info("Connected to warehouse")

    def setup(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(_CREATE_SCHEMA)
            cur.execute(_CREATE_TABLE)
            cur.execute(_ADD_COLUMNS)
        self._conn.commit()
        logger.info("Schema and table initialised")

    def load(self, observations: List[WeatherObservation]) -> int:
        if not observations:
            logger.warning("No observations to load — skipping")
            return 0

        rows = [
            (
                o.city_name, o.latitude, o.longitude, o.observed_at,
                o.temperature_celsius, o.apparent_temperature, o.relative_humidity_pct,
                o.precipitation_mm, o.wind_speed_kmh,
            )
            for o in observations
        ]
        with self._conn.cursor() as cur:
            execute_values(cur, _UPSERT, rows)
        self._conn.commit()
        logger.info("Loaded %d rows into raw.weather_observations", len(rows))
        return len(rows)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            logger.info("Warehouse connection closed")

    def __enter__(self) -> "WarehouseLoader":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()
