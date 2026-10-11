
-- GeoPulse: Hourly Lekki Catchment Overlap
-- Purpose: Examine shared synthetic device observations by UTC hour.
-- Note: This is not verified customer traffic or store visitation.

WITH lekki_pings AS (
    SELECT
        StoreID,
        DeviceID,
        Timestamp,
        EXTRACT(HOUR FROM Timestamp) AS hour_utc
    FROM
        `careflow-process-mining-509421.geopulse_raw.store_catchments`
    WHERE
        StoreID IN ('STORE_001', 'STORE_002')
),

shared_devices AS (
    SELECT DISTINCT
        a.DeviceID
    FROM lekki_pings AS a
    INNER JOIN lekki_pings AS b
        ON a.DeviceID = b.DeviceID
    WHERE
        a.StoreID = 'STORE_001'
        AND b.StoreID = 'STORE_002'
),

hourly_summary AS (
    SELECT
        p.hour_utc,
        COUNTIF(p.StoreID = 'STORE_001') AS store_a_pings,
        COUNTIF(p.StoreID = 'STORE_002') AS store_b_pings,
        COUNTIF(
            p.StoreID = 'STORE_001'
            AND s.DeviceID IS NOT NULL
        ) AS store_a_pings_from_shared_devices,
        COUNTIF(
            p.StoreID = 'STORE_002'
            AND s.DeviceID IS NOT NULL
        ) AS store_b_pings_from_shared_devices,
        COUNT(DISTINCT IF(
            p.StoreID = 'STORE_001', p.DeviceID, NULL
        )) AS store_a_devices,
        COUNT(DISTINCT IF(
            p.StoreID = 'STORE_002', p.DeviceID, NULL
        )) AS store_b_devices,
        COUNT(DISTINCT IF(
            s.DeviceID IS NOT NULL, p.DeviceID, NULL
        )) AS shared_devices_observed_that_hour
    FROM lekki_pings AS p
    LEFT JOIN shared_devices AS s
        ON p.DeviceID = s.DeviceID
    GROUP BY p.hour_utc
)

SELECT
    hour_utc,
    store_a_pings,
    store_b_pings,
    store_a_pings_from_shared_devices,
    store_b_pings_from_shared_devices,
    store_a_devices,
    store_b_devices,
    shared_devices_observed_that_hour
FROM hourly_summary
ORDER BY hour_utc;