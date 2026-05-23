from dataclasses import dataclass
from datetime import datetime
from typing import List

import requests

from ..logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class WeatherObservation:
    city_name: str
    latitude: float
    longitude: float
    observed_at: datetime
    temperature_celsius: float
    precipitation_mm: float
    wind_speed_kmh: float


class OpenMeteoClient:
    def __init__(self) -> None:
        self._session = requests.Session()

    def fetch_weather(
        self,
        city_name: str,
        latitude: float,
        longitude: float,
        past_days: int = 7,
    ) -> List[WeatherObservation]:
        logger.info("Fetching weather for %s (%.4f, %.4f)", city_name, latitude, longitude)

        resp = self._session.get(
            BASE_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,precipitation,wind_speed_10m",
                "past_days": past_days,
                "forecast_days": 1,
                "timezone": "UTC",
            },
            timeout=30,
        )
        resp.raise_for_status()
        hourly = resp.json()["hourly"]

        observations = [
            WeatherObservation(
                city_name=city_name,
                latitude=latitude,
                longitude=longitude,
                observed_at=datetime.fromisoformat(ts),
                temperature_celsius=temp,
                precipitation_mm=precip or 0.0,
                wind_speed_kmh=wind or 0.0,
            )
            for ts, temp, precip, wind in zip(
                hourly["time"],
                hourly["temperature_2m"],
                hourly["precipitation"],
                hourly["wind_speed_10m"],
            )
            if temp is not None
        ]

        logger.info("Fetched %d observations for %s", len(observations), city_name)
        return observations
