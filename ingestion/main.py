import sys

from src.config import load_config
from src.logger import get_logger
from src.pipelines.weather import WeatherPipeline

logger = get_logger("main")


def main() -> int:
    logger.info("=== Weather Analytics — Ingestion ===")
    config = load_config()
    total = WeatherPipeline(config).run()
    logger.info("=== Done. %d rows ingested ===", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
