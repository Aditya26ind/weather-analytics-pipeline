import os
import pytest
from src.config import load_config, Config, CityConfig


def test_defaults():
    for key in ("WAREHOUSE_HOST", "WAREHOUSE_PORT", "WAREHOUSE_USER",
                "WAREHOUSE_PASSWORD", "WAREHOUSE_DB", "PAST_DAYS"):
        os.environ.pop(key, None)

    cfg = load_config()

    assert cfg.warehouse_host == "localhost"
    assert cfg.warehouse_port == 5432
    assert cfg.warehouse_user == "warehouse"
    assert cfg.warehouse_password == "warehouse"
    assert cfg.warehouse_db == "analytics"
    assert cfg.past_days == 7
    assert len(cfg.cities) == 10


def test_env_override(monkeypatch):
    monkeypatch.setenv("WAREHOUSE_HOST", "myhost")
    monkeypatch.setenv("WAREHOUSE_PORT", "5433")
    monkeypatch.setenv("PAST_DAYS", "14")

    cfg = load_config()

    assert cfg.warehouse_host == "myhost"
    assert cfg.warehouse_port == 5433
    assert cfg.past_days == 14


def test_cities_have_required_fields():
    cfg = load_config()
    for city in cfg.cities:
        assert isinstance(city, CityConfig)
        assert city.name
        assert -90 <= city.latitude <= 90
        assert -180 <= city.longitude <= 180


def test_city_names():
    cfg = load_config()
    names = [c.name for c in cfg.cities]
    assert "New York" in names
    assert "London" in names
    assert "Tokyo" in names
    assert "Paris" in names
    assert "Berlin" in names
    assert "Singapore" in names
    assert "Dubai" in names
    assert "Sao Paulo" in names
