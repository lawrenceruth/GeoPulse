
-- Standardize synthetic GPS pings matched to store catchments.
-- Source data remains unchanged in geopulse_raw.

SELECT
    StoreID AS store_id,
    StoreName AS store_name,
    DeviceID AS device_id,
    Timestamp AS ping_timestamp,
    distance_meters
FROM {{ source('geopulse_raw', 'store_catchments') }}
