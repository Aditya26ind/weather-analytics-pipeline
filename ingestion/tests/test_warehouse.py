from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

from src.clients.open_meteo import WeatherObservation
from src.config import Config, CityConfig
from src.loaders.warehouse import WarehouseLoader


def _make_config(**overrides):
    defaults = dict(
        warehouse_host="localhost",
        warehouse_port=5432,
        warehouse_user="u",
        warehouse_password="p",
        warehouse_db="db",
        past_days=7,
        cities=[],
    )
    defaults.update(overrides)
    return Config(**defaults)


def _make_observation(**overrides):
    defaults = dict(
        city_name="TestCity",
        latitude=40.0,
        longitude=-74.0,
        observed_at=datetime(2024, 1, 1, 12, 0),
        temperature_celsius=20.0,
        apparent_temperature=18.5,
        relative_humidity_pct=65.0,
        precipitation_mm=0.5,
        wind_speed_kmh=10.0,
    )
    defaults.update(overrides)
    return WeatherObservation(**defaults)


@patch("src.loaders.warehouse.psycopg2.connect")
def test_connect_uses_config(mock_connect):
    cfg = _make_config(warehouse_host="myhost", warehouse_port=5433)
    loader = WarehouseLoader(cfg)
    loader.connect()

    mock_connect.assert_called_once_with(
        host="myhost",
        port=5433,
        user="u",
        password="p",
        dbname="db",
    )


@patch("src.loaders.warehouse.psycopg2.connect")
def test_setup_creates_schema_and_table(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    loader = WarehouseLoader(_make_config())
    loader.connect()
    loader.setup()

    assert mock_cur.execute.call_count == 3
    first_sql = mock_cur.execute.call_args_list[0][0][0]
    assert "CREATE SCHEMA" in first_sql
    second_sql = mock_cur.execute.call_args_list[1][0][0]
    assert "CREATE TABLE" in second_sql
    third_sql = mock_cur.execute.call_args_list[2][0][0]
    assert "ALTER TABLE" in third_sql
    mock_conn.commit.assert_called_once()


@patch("src.loaders.warehouse.execute_values")
@patch("src.loaders.warehouse.psycopg2.connect")
def test_load_returns_row_count(mock_connect, mock_execute_values):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    obs = [_make_observation(), _make_observation(city_name="London")]
    loader = WarehouseLoader(_make_config())
    loader.connect()
    count = loader.load(obs)

    assert count == 2
    mock_execute_values.assert_called_once()
    mock_conn.commit.assert_called_once()


@patch("src.loaders.warehouse.psycopg2.connect")
def test_load_empty_observations_returns_zero(mock_connect):
    loader = WarehouseLoader(_make_config())
    loader._conn = MagicMock()
    count = loader.load([])
    assert count == 0
    loader._conn.cursor.assert_not_called()


@patch("src.loaders.warehouse.psycopg2.connect")
def test_context_manager_connects_and_closes(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    with WarehouseLoader(_make_config()) as loader:
        pass

    mock_conn.close.assert_called_once()
