-- Match GPS pings that fall within 500 metres of each synthetic store.
-- A ping can match multiple stores if their catchments overlap.
CREATE OR REPLACE TABLE
  `careflow-process-mining-509421.geopulse_raw.store_catchments`
AS
SELECT
  s.StoreID,
  s.StoreName,
  p.DeviceID,
  p.Timestamp,
  ST_DISTANCE(p.location, s.location) AS distance_meters
FROM
  `careflow-process-mining-509421.geopulse_raw.gps_pings_spatial` AS p
CROSS JOIN
  `careflow-process-mining-509421.geopulse_raw.store_locations` AS s
WHERE
  ST_DWITHIN(p.location, s.location, 500);
