
-- Summarize synthetic GPS pings matched to each store's 500m catchment.
-- These metrics describe simulated location data, not verified visits.

SELECT
    store_id,
    store_name,
    COUNT(*) AS matched_gps_pings,
    COUNT(DISTINCT device_id) AS unique_devices,
    ROUND(AVG(distance_meters), 2) AS avg_distance_meters,
    ROUND(MIN(distance_meters), 2) AS min_distance_meters,
    ROUND(MAX(distance_meters), 2) AS max_distance_meters,
    MIN(ping_timestamp) AS first_ping_timestamp,
    MAX(ping_timestamp) AS last_ping_timestamp
FROM {{ ref('stg_store_catchments') }}
GROUP BY
    store_id,
    store_name
