import os
from dataclasses import dataclass, field
from typing import List
from typing import Optional


@dataclass
class CityConfig:
    name: str
    latitude: float
    longitude: float


@dataclass
class Config:
    warehouse_host: str
    warehouse_port: int
    warehouse_user: str
    warehouse_password: str
    warehouse_db: str
    past_days: int
    cities: List[CityConfig] = field(default_factory=list)
    metrics_port: Optional[int] = None


def load_config() -> Config:
    return Config(
        warehouse_host=os.environ.get("WAREHOUSE_HOST", "localhost"),
        warehouse_port=int(os.environ.get("WAREHOUSE_PORT", "5432")),
        warehouse_user=os.environ.get("WAREHOUSE_USER", "warehouse"),
        warehouse_password=os.environ.get("WAREHOUSE_PASSWORD", "warehouse"),
        warehouse_db=os.environ.get("WAREHOUSE_DB", "analytics"),
        past_days=int(os.environ.get("PAST_DAYS", "7")),
        cities=[
            CityConfig("New York", 40.7128, -74.0060),
            CityConfig("London", 51.5074, -0.1278),
            CityConfig("Tokyo", 35.6762, 139.6503),
            CityConfig("Sydney", -33.8688, 151.2093),
            CityConfig("Mumbai", 19.0760, 72.8777),
            CityConfig("Paris", 48.8566, 2.3522),
            CityConfig("Berlin", 52.5200, 13.4050),
            CityConfig("Singapore", 1.3521, 103.8198),
            CityConfig("Dubai", 25.2048, 55.2708),
            CityConfig("Sao Paulo", -23.5505, -46.6333),
        ],
        metrics_port=(int(os.environ.get("METRICS_PORT")) if os.environ.get("METRICS_PORT") else None),
    )
