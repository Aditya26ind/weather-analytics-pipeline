"""
Daily weather pipeline DAG.

Flow:  ingest → dbt deps → dbt run → dbt snapshot → dbt test

The ingestion step is a PythonOperator that imports the pipeline code directly
(mounted at /opt/ingestion_src).  dbt steps are BashOperators pointing at the
dbt project mounted at /dbt.
"""

import sys
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

sys.path.insert(0, "/opt/ingestion_src")

DBT_CMD = "dbt {subcmd} --project-dir /dbt --profiles-dir /dbt"

DEFAULT_ARGS = {
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="weather_pipeline",
    description="Ingest hourly weather data and run dbt transformations",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["weather", "etl"],
)
def weather_pipeline():
    @task()
    def ingest() -> int:
        from config import load_config
        from pipelines.weather import WeatherPipeline

        config = load_config()
        rows = WeatherPipeline(config).run()
        return rows

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=DBT_CMD.format(subcmd="deps"),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=DBT_CMD.format(subcmd="run"),
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=DBT_CMD.format(subcmd="snapshot"),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=DBT_CMD.format(subcmd="test"),
    )

    ingest() >> dbt_deps >> dbt_run >> dbt_snapshot >> dbt_test


weather_pipeline()
