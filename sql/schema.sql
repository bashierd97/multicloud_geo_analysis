-- schema.sql
-- Stand up the spatial table by hand if you would rather not use the Python
-- loader. The Python loader does the same thing, this is here to show you can
-- write the DDL yourself.

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS cloud_regions;

CREATE TABLE cloud_regions (
    id           SERIAL PRIMARY KEY,
    provider     TEXT NOT NULL,
    region_code  TEXT NOT NULL UNIQUE,
    region_name  TEXT NOT NULL,
    location     TEXT,
    country      TEXT,
    latitude     DOUBLE PRECISION NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    -- Point geometry in WGS84 (SRID 4326).
    geometry     geometry(Point, 4326)
);

-- Fill the geometry column from the lat/long after a plain COPY of the CSV.
-- Example loading flow:
--   \copy cloud_regions(provider,region_code,region_name,location,country,latitude,longitude)
--       FROM 'data/cloud_regions.csv' CSV HEADER;
--   UPDATE cloud_regions
--       SET geometry = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);

-- The spatial index. Every nearest neighbor and radius query leans on this.
CREATE INDEX IF NOT EXISTS cloud_regions_geom_idx
    ON cloud_regions USING GIST (geometry);
