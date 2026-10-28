
-- GeoPulse: Geographic overlap between the two Lekki catchments.
-- Measures polygon intersection, not customer or sales cannibalization.

WITH lekki_catchments AS (
    SELECT
        StoreID,
        StoreName,
        catchment_geometry
    FROM
        `careflow-process-mining-509421.geopulse_raw.store_catchment_areas`
    WHERE
        StoreID IN ('STORE_001', 'STORE_002')
),

store_a AS (
    SELECT *
    FROM lekki_catchments
    WHERE StoreID = 'STORE_001'
),

store_b AS (
    SELECT *
    FROM lekki_catchments
    WHERE StoreID = 'STORE_002'
),

overlap AS (
    SELECT
        a.StoreName AS store_a,
        b.StoreName AS store_b,
        ST_AREA(a.catchment_geometry) AS area_a_sqm,
        ST_AREA(b.catchment_geometry) AS area_b_sqm,
        ST_AREA(
            ST_INTERSECTION(
                a.catchment_geometry,
                b.catchment_geometry
            )
        ) AS overlap_area_sqm
    FROM store_a AS a
    CROSS JOIN store_b AS b
)

SELECT
    store_a,
    store_b,
    ROUND(area_a_sqm, 2) AS store_a_area_sqm,
    ROUND(area_b_sqm, 2) AS store_b_area_sqm,
    ROUND(overlap_area_sqm, 2) AS shared_area_sqm,
    ROUND(
        SAFE_DIVIDE(overlap_area_sqm, area_a_sqm) * 100,
        2
    ) AS pct_store_a_area_overlapping,
    ROUND(
        SAFE_DIVIDE(overlap_area_sqm, area_b_sqm) * 100,
        2
    ) AS pct_store_b_area_overlapping
FROM overlap;
