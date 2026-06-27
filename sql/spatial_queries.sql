-- spatial_queries.sql
-- The same four questions from spatial_analysis.py, answered in the database.
-- These are the queries worth showing in an interview because they use the
-- spatial index instead of scanning every row.
--
-- Note on units. The geometry is in degrees (SRID 4326), so we cast to
-- geography for true meter distances. geography math is on the real globe.


-- 1. Nearest region to a customer point (San Diego shown here).
--    The <-> operator is index assisted KNN. ORDER BY ... LIMIT 1 is the
--    fast nearest neighbor pattern in PostGIS.
SELECT
    region_code,
    provider,
    region_name,
    ROUND(
        (geometry::geography <-> ST_SetSRID(ST_MakePoint(-117.16, 32.72), 4326)::geography)
        / 1000.0
    )::int AS distance_km
FROM cloud_regions
ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(-117.16, 32.72), 4326)
LIMIT 1;


-- 2. Pairwise distances between every region (latency proxy matrix).
--    Self join, keep one side of each pair with a.id < b.id.
SELECT
    a.region_code AS region_a,
    b.region_code AS region_b,
    ROUND((a.geometry::geography <-> b.geometry::geography) / 1000.0)::int AS distance_km
FROM cloud_regions a
JOIN cloud_regions b ON a.id < b.id
ORDER BY distance_km
LIMIT 20;


-- 3. Coverage. Regions within 2000 km of a city (Singapore shown here).
--    ST_DWithin on geography is index assisted and takes meters.
SELECT
    region_code,
    provider,
    ROUND(
        (geometry::geography <-> ST_SetSRID(ST_MakePoint(103.82, 1.35), 4326)::geography)
        / 1000.0
    )::int AS distance_km
FROM cloud_regions
WHERE ST_DWithin(
    geometry::geography,
    ST_SetSRID(ST_MakePoint(103.82, 1.35), 4326)::geography,
    2000000  -- 2000 km in meters
)
ORDER BY distance_km;


-- 4. Per provider footprint. Count, center of mass, and how wide each spreads.
SELECT
    provider,
    COUNT(*) AS region_count,
    ROUND(ST_Y(ST_Centroid(ST_Collect(geometry)))::numeric, 3) AS centroid_lat,
    ROUND(ST_X(ST_Centroid(ST_Collect(geometry)))::numeric, 3) AS centroid_lon
FROM cloud_regions
GROUP BY provider
ORDER BY region_count DESC;
