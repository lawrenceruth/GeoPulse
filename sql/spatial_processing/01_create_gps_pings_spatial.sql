-- Create a spatially prepared GPS table with BigQuery GEOGRAPHY points.
CREATE OR REPLACE TABLE
  `careflow-process-mining-509421.geopulse_raw.gps_pings_spatial`
AS
SELECT
  DeviceID,
  Latitude,
  Longitude,
  Timestamp,
  ST_GEOGPOINT(Longitude, Latitude) AS location
FROM
  `careflow-process-mining-509421.geopulse_raw.gps_pings`
WHERE
  Latitude BETWEEN -90 AND 90
  AND Longitude BETWEEN -180 AND 180
  AND Latitude IS NOT NULL
  AND Longitude IS NOT NULL
  AND Timestamp IS NOT NULL;
