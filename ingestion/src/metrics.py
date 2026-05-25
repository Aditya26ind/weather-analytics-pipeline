from prometheus_client import Counter, start_http_server
from typing import Optional
import threading

# Prometheus metrics
API_REQUESTS = Counter("open_meteo_api_requests_total", "Total Open-Meteo API requests", ["city"])  # type: ignore
API_ERRORS = Counter("open_meteo_api_errors_total", "Total Open-Meteo API errors", ["city"])  # type: ignore
OBSERVATIONS_FETCHED = Counter("observations_fetched_total", "Total observations fetched", ["city"])  # type: ignore
ROWS_LOADED = Counter("warehouse_rows_loaded_total", "Total rows loaded into the warehouse")  # type: ignore
PIPELINE_ERRORS = Counter("pipeline_errors_total", "Total pipeline errors")  # type: ignore


def start_metrics_server(port: Optional[int]) -> None:
    if not port:
        return

    def _start():
        start_http_server(port)

    thread = threading.Thread(target=_start, daemon=True)
    thread.start()
