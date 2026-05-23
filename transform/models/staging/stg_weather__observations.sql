WITH source AS (
    SELECT * FROM {{ source('raw', 'weather_observations') }}
),

cleaned AS (
    SELECT
        id                              AS observation_id,
        city_name,
        latitude,
        longitude,
        observed_at::timestamp          AS observed_at,
        temperature_celsius,
        COALESCE(precipitation_mm, 0.0) AS precipitation_mm,
        COALESCE(wind_speed_kmh, 0.0)   AS wind_speed_kmh,
        ingested_at
    FROM source
    WHERE observed_at         IS NOT NULL
      AND temperature_celsius IS NOT NULL
)

SELECT * FROM cleaned
