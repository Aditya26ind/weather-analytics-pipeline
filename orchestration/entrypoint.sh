#!/bin/bash
set -e

# Create Airflow metadata database in the warehouse Postgres if it doesn't exist
PGPASSWORD="${WAREHOUSE_PASSWORD}" psql \
  -h "${WAREHOUSE_HOST}" \
  -U "${WAREHOUSE_USER}" \
  -tc "SELECT 1 FROM pg_database WHERE datname='airflow'" \
  | grep -q 1 \
  || PGPASSWORD="${WAREHOUSE_PASSWORD}" psql \
     -h "${WAREHOUSE_HOST}" \
     -U "${WAREHOUSE_USER}" \
     -c "CREATE DATABASE airflow;"

exec airflow standalone
