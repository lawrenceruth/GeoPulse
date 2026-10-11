-- Create 500-metre buffer polygons around each synthetic store.
CREATE OR REPLACE TABLE
  `careflow-process-mining-509421.geopulse_raw.store_catchment_areas`
AS
SELECT
  StoreID,
  StoreName,
  ST_BUFFER(location, 500) AS catchment_geometry,
  500 AS radius_meters
FROM
  `careflow-process-mining-509421.geopulse_raw.store_locations`;
