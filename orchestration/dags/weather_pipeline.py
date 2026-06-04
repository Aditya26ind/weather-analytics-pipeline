"""
Daily weather pipeline DAG.

Flow:  ingest_<pipeline> (all in parallel) → dbt deps → dbt run → dbt snapshot → dbt test

Ingestion tasks are auto-discovered: any module in /opt/ingestion_src/pipelines/ that
contains a class ending in 'Pipeline' with a run() method is picked up automatically.
Drop a new pipeline file there and it appears as a task on the next DAG parse — no edits here.
"""

import importlib
import inspect
import pkgutil
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

PIPELINES_PKG = "pipelines"


def _discover_pipeline_classes() -> list[tuple[str, type]]:
    """Return [(task_id, PipelineClass)] for every *Pipeline class found in the pipelines package."""
    import pipelines  # noqa: PLC0415 — intentional late import after sys.path is set

    results = []
    pkg_path = pipelines.__path__
    for _, module_name, _ in pkgutil.iter_modules(pkg_path):
        module = importlib.import_module(f"{PIPELINES_PKG}.{module_name}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.endswith("Pipeline") and hasattr(obj, "run"):
                task_id = f"ingest_{module_name}"
                results.append((task_id, obj))
    return results


@dag(
    dag_id="weather_pipeline",
    description="Ingest data from all discovered pipelines and run dbt transformations",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["weather", "etl"],
)
def weather_pipeline():
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

    ingest_tasks = []
    for task_id, pipeline_cls in _discover_pipeline_classes():
        # Capture pipeline_cls in default arg to avoid closure over loop variable
        @task(task_id=task_id)
        def run_pipeline(cls=pipeline_cls) -> int:
            from config import load_config
            config = load_config()
            return cls(config).run()

        ingest_tasks.append(run_pipeline())

    # All ingestion tasks run in parallel, then dbt runs sequentially
    ingest_tasks >> dbt_deps >> dbt_run >> dbt_snapshot >> dbt_test


weather_pipeline()
