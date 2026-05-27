{{
    config(materialized='table')
}}

WITH daily AS (
    SELECT * FROM {{ ref('int_weather__daily_aggregates') }}
),

ranked AS (
    SELECT
        city_name,
        observation_date,
        max_temp_celsius,
        min_temp_celsius,
        max_apparent_temp_celsius,
        min_apparent_temp_celsius,
        avg_relative_humidity_pct,
        total_precipitation_mm,
        avg_wind_speed_kmh,

        RANK() OVER (PARTITION BY city_name ORDER BY max_temp_celsius DESC)         AS hottest_rank,
        RANK() OVER (PARTITION BY city_name ORDER BY min_temp_celsius ASC)          AS coldest_rank,
        RANK() OVER (PARTITION BY city_name ORDER BY total_precipitation_mm DESC)   AS wettest_rank,
        RANK() OVER (PARTITION BY city_name ORDER BY avg_relative_humidity_pct DESC) AS most_humid_rank,
        RANK() OVER (PARTITION BY city_name ORDER BY avg_wind_speed_kmh DESC)       AS windiest_rank
    FROM daily
)

SELECT
    city_name,
    observation_date,
    max_temp_celsius,
    min_temp_celsius,
    max_apparent_temp_celsius,
    min_apparent_temp_celsius,
    avg_relative_humidity_pct,
    total_precipitation_mm,
    avg_wind_speed_kmh,
    hottest_rank,
    coldest_rank,
    wettest_rank,
    most_humid_rank,
    windiest_rank,
    -- convenience flag: top-5 in any extreme category
    (
        hottest_rank    <= 5
        OR coldest_rank  <= 5
        OR wettest_rank  <= 5
        OR most_humid_rank <= 5
        OR windiest_rank <= 5
    ) AS is_notable_day
FROM ranked
WHERE
    hottest_rank    <= 5
    OR coldest_rank  <= 5
    OR wettest_rank  <= 5
    OR most_humid_rank <= 5
    OR windiest_rank <= 5
ORDER BY
    city_name,
    observation_date
