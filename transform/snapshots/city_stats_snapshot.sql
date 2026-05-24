{% snapshot city_stats_snapshot %}

{{
    config(
        unique_key='city_name',
        strategy='check',
        check_cols='all',
    )
}}

/*
  SCD Type 2 snapshot of mart_weather__city_stats.

  Each time a city's aggregate stats change (new days of data, updated
  temperature extremes, accumulated precipitation, etc.) dbt closes the
  previous record by setting dbt_valid_to and inserts a new open record
  with dbt_valid_from = now().  This lets you answer questions like:
  "What was London's all-time max temp as of last Tuesday?"
*/

SELECT * FROM {{ ref('mart_weather__city_stats') }}

{% endsnapshot %}
