
-- GeoPulse: Lekki Store Cannibalization Analysis
-- Purpose: Measure shared synthetic device observations between
-- the two nearby stores within their 500-metre catchments.
--
-- Important: Shared observations indicate potential audience overlap,
-- not verified customer switching or lost sales.

WITH lekki_a AS (
    SELECT
        DeviceID,
        COUNT(*) AS pings_near_store_a
    FROM
        `careflow-process-mining-509421.geopulse_raw.store_catchments`
    WHERE
        StoreID = 'STORE_001'
    GROUP BY
        DeviceID
),

lekki_b AS (
    SELECT
        DeviceID,
        COUNT(*) AS pings_near_store_b
    FROM
        `careflow-process-mining-509421.geopulse_raw.store_catchments`
    WHERE
        StoreID = 'STORE_002'
    GROUP BY
        DeviceID
),

overlap_summary AS (
    SELECT
        COUNT(*) AS shared_devices,
        SUM(pings_near_store_a) AS shared_device_pings_a,
        SUM(pings_near_store_b) AS shared_device_pings_b
    FROM lekki_a
    INNER JOIN lekki_b
        USING (DeviceID)
)

SELECT
    a_devices AS unique_devices_near_a,
    b_devices AS unique_devices_near_b,
    shared_devices,
    ROUND(
        SAFE_DIVIDE(shared_devices, a_devices) * 100, 2
    ) AS pct_a_devices_also_near_b,
    ROUND(
        SAFE_DIVIDE(shared_devices, b_devices) * 100, 2
    ) AS pct_b_devices_also_near_a,
    shared_device_pings_a,
    shared_device_pings_b
FROM (
    SELECT
        (SELECT COUNT(*) FROM lekki_a) AS a_devices,
        (SELECT COUNT(*) FROM lekki_b) AS b_devices,
        shared_devices,
        shared_device_pings_a,
        shared_device_pings_b
    FROM overlap_summary
);
