-- Create five synthetic store locations with geographic point columns.
CREATE OR REPLACE TABLE
  `careflow-process-mining-509421.geopulse_raw.store_locations`
AS
WITH synthetic_stores AS (
  SELECT *
  FROM UNNEST([
    STRUCT(
      'STORE_001' AS StoreID,
      'GeoPulse Lekki A' AS StoreName,
      6.4474 AS Latitude,
      3.4723 AS Longitude
    ),
    STRUCT(
      'STORE_002' AS StoreID,
      'GeoPulse Lekki B' AS StoreName,
      6.4485 AS Latitude,
      3.4730 AS Longitude
    ),
    STRUCT(
      'STORE_003' AS StoreID,
      'GeoPulse Victoria Island' AS StoreName,
      6.4281 AS Latitude,
      3.4219 AS Longitude
    ),
    STRUCT(
      'STORE_004' AS StoreID,
      'GeoPulse Ikeja' AS StoreName,
      6.6018 AS Latitude,
      3.3515 AS Longitude
    ),
    STRUCT(
      'STORE_005' AS StoreID,
      'GeoPulse Yaba' AS StoreName,
      6.5095 AS Latitude,
      3.3711 AS Longitude
    )
  ])
)
SELECT
  StoreID,
  StoreName,
  Latitude,
  Longitude,
  ST_GEOGPOINT(Longitude, Latitude) AS location
FROM synthetic_stores;
