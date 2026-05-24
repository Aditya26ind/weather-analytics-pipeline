FROM apache/airflow:2.9.0-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER airflow
COPY requirements.txt /tmp/orchestration_requirements.txt
RUN pip install --no-cache-dir -r /tmp/orchestration_requirements.txt

ENTRYPOINT ["/entrypoint.sh"]
