from ..clients.open_meteo import OpenMeteoClient
from ..config import Config
from ..loaders.warehouse import WarehouseLoader
from ..logger import get_logger

logger = get_logger(__name__)


class WeatherPipeline:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OpenMeteoClient()

    def run(self) -> int:
        logger.info("Starting weather pipeline for %d cities", len(self._config.cities))
        total = 0

        with WarehouseLoader(self._config) as loader:
            loader.setup()

            for city in self._config.cities:
                try:
                    observations = self._client.fetch_weather(
                        city_name=city.name,
                        latitude=city.latitude,
                        longitude=city.longitude,
                        past_days=self._config.past_days,
                    )
                    total += loader.load(observations)
                except Exception:
                    logger.exception("Failed to process city=%s — continuing", city.name)

        logger.info("Pipeline complete. Total rows loaded: %d", total)
        return total
