WITH observations AS (
    SELECT * FROM {{ ref('stg_weather__observations') }}
)

SELECT
    city_name,
    observed_at::date                               AS observation_date,
    ROUND(AVG(temperature_celsius)::numeric, 2)     AS avg_temp_celsius,
    ROUND(MAX(temperature_celsius)::numeric, 2)     AS max_temp_celsius,
    ROUND(MIN(temperature_celsius)::numeric, 2)     AS min_temp_celsius,
    ROUND(SUM(precipitation_mm)::numeric, 2)        AS total_precipitation_mm,
    ROUND(AVG(wind_speed_kmh)::numeric, 2)          AS avg_wind_speed_kmh,
    COUNT(*)                                        AS hourly_readings
FROM observations
GROUP BY
    city_name,
    observed_at::date
