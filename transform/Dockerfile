FROM python:3.11-slim

WORKDIR /dbt

RUN pip install --no-cache-dir "dbt-postgres==1.7.0" "protobuf<5.26"

COPY . .

ENV DBT_PROFILES_DIR=/dbt

RUN dbt deps

ENTRYPOINT ["dbt"]
CMD ["run"]
