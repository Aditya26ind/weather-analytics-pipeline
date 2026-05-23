from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.clients.open_meteo import OpenMeteoClient, WeatherObservation


MOCK_RESPONSE = {
    "hourly": {
        "time": ["2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00"],
        "temperature_2m": [10.5, 11.0, None],
        "precipitation": [0.0, 1.2, 0.5],
        "wind_speed_10m": [5.0, None, 8.0],
    }
}


def _make_client_with_mock(json_data):
    client = OpenMeteoClient()
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status.return_value = None
    client._session.get = MagicMock(return_value=mock_resp)
    return client


def test_returns_observations():
    client = _make_client_with_mock(MOCK_RESPONSE)
    obs = client.fetch_weather("TestCity", 40.0, -74.0, past_days=1)
    assert len(obs) == 2  # third row has None temperature — filtered out


def test_observation_fields():
    client = _make_client_with_mock(MOCK_RESPONSE)
    obs = client.fetch_weather("TestCity", 40.0, -74.0)

    first = obs[0]
    assert first.city_name == "TestCity"
    assert first.latitude == 40.0
    assert first.longitude == -74.0
    assert first.temperature_celsius == 10.5
    assert first.precipitation_mm == 0.0
    assert first.wind_speed_kmh == 5.0
    assert isinstance(first.observed_at, datetime)


def test_null_precip_and_wind_default_to_zero():
    client = _make_client_with_mock(MOCK_RESPONSE)
    obs = client.fetch_weather("TestCity", 40.0, -74.0)

    second = obs[1]
    assert second.precipitation_mm == 1.2
    assert second.wind_speed_kmh == 0.0  # None → 0.0


def test_api_called_with_correct_params():
    client = _make_client_with_mock(MOCK_RESPONSE)
    client.fetch_weather("London", 51.5, -0.1, past_days=3)

    call_kwargs = client._session.get.call_args
    params = call_kwargs[1]["params"]
    assert params["latitude"] == 51.5
    assert params["longitude"] == -0.1
    assert params["past_days"] == 3
    assert "temperature_2m" in params["hourly"]


def test_empty_hourly_data():
    empty_response = {
        "hourly": {
            "time": [],
            "temperature_2m": [],
            "precipitation": [],
            "wind_speed_10m": [],
        }
    }
    client = _make_client_with_mock(empty_response)
    obs = client.fetch_weather("Empty", 0.0, 0.0)
    assert obs == []


def test_http_error_propagates():
    client = OpenMeteoClient()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 429")
    client._session.get = MagicMock(return_value=mock_resp)

    with pytest.raises(Exception, match="HTTP 429"):
        client.fetch_weather("Err", 0.0, 0.0)
