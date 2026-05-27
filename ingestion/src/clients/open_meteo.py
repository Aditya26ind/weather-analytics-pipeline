from dataclasses import dataclass
from datetime import datetime
from typing import List

import requests
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

from ..logger import get_logger
from ..metrics import API_REQUESTS, API_ERRORS, OBSERVATIONS_FETCHED

logger = get_logger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


class RateLimitError(Exception):
    pass


@dataclass
class WeatherObservation:
    city_name: str
    latitude: float
    longitude: float
    observed_at: datetime
    temperature_celsius: float
    apparent_temperature: float
    relative_humidity_pct: float
    precipitation_mm: float
    wind_speed_kmh: float


class OpenMeteoClient:
    def __init__(self) -> None:
        self._session = requests.Session()

    @retry(
        retry=retry_if_exception_type((requests.exceptions.RequestException, RateLimitError)),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _get_with_retries(self, params: dict, city_name: str) -> dict:
        API_REQUESTS.labels(city=city_name).inc()
        resp = self._session.get(BASE_URL, params=params, timeout=30)
        if resp.status_code == 429:
            API_ERRORS.labels(city=city_name).inc()
            logger.warning("Rate limited by Open-Meteo for city=%s", city_name)
            raise RateLimitError("rate limited")
        resp.raise_for_status()
        return resp.json()

    def fetch_weather(
        self,
        city_name: str,
        latitude: float,
        longitude: float,
        past_days: int = 7,
    ) -> List[WeatherObservation]:
        logger.info("Fetching weather for %s (%.4f, %.4f)", city_name, latitude, longitude)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m",
            "past_days": past_days,
            "forecast_days": 1,
            "timezone": "UTC",
        }

        data = self._get_with_retries(params=params, city_name=city_name)
        hourly = data.get("hourly", {})

        observations = [
            WeatherObservation(
                city_name=city_name,
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime.fromisoformat(ts),
                temperature_celsius=temp,
                apparent_temperature=apparent or temp,
                relative_humidity_pct=float(humidity or 0),
                precipitation_mm=precip or 0.0,
                wind_speed_kmh=wind or 0.0,
            )
            for ts, temp, apparent, humidity, precip, wind in zip(
                hourly.get("time", []),
                hourly.get("temperature_2m", []),
                hourly.get("apparent_temperature", []),
                hourly.get("relative_humidity_2m", []),
                hourly.get("precipitation", []),
                hourly.get("wind_speed_10m", []),
            )
            if temp is not None
        ]

        OBSERVATIONS_FETCHED.labels(city=city_name).inc(len(observations))
        logger.info("Fetched %d observations for %s", len(observations), city_name)
        return observations
