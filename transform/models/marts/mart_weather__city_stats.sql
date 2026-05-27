WITH daily AS (
    SELECT * FROM {{ ref('int_weather__daily_aggregates') }}
)

SELECT
    city_name,
    COUNT(DISTINCT observation_date)                        AS days_tracked,
    MIN(observation_date)                                   AS tracking_start_date,
    MAX(observation_date)                                   AS tracking_end_date,
    ROUND(AVG(avg_temp_celsius)::numeric, 2)                AS avg_temp_celsius,
    MAX(max_temp_celsius)                                   AS all_time_max_temp_celsius,
    MIN(min_temp_celsius)                                   AS all_time_min_temp_celsius,
    ROUND(
        (MAX(max_temp_celsius) - MIN(min_temp_celsius))::numeric, 2
    )                                                       AS temp_range_celsius,
    ROUND(AVG(avg_apparent_temp_celsius)::numeric, 2)       AS avg_apparent_temp_celsius,
    MAX(max_apparent_temp_celsius)                          AS all_time_max_apparent_temp_celsius,
    MIN(min_apparent_temp_celsius)                          AS all_time_min_apparent_temp_celsius,
    ROUND(AVG(avg_relative_humidity_pct)::numeric, 2)       AS avg_relative_humidity_pct,
    ROUND(SUM(total_precipitation_mm)::numeric, 2)          AS total_precipitation_mm,
    ROUND(AVG(avg_wind_speed_kmh)::numeric, 2)              AS avg_wind_speed_kmh
FROM daily
GROUP BY city_name
ORDER BY city_name
