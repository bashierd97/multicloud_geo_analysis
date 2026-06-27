"""
load_regions.py

Read the raw cloud region CSV, validate it, turn it into a GeoDataFrame,
and write it out as a GeoPackage that every other script in this project reads.

This is the front door of the pipeline. Everything downstream assumes the
GeoPackage exists and is in EPSG:4326 (plain lat/long on the WGS84 globe).

Run:
    python src/load_regions.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# WGS84. Lat/long degrees. The standard for raw GPS style coordinates.
WGS84 = "EPSG:4326"

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "cloud_regions.csv"
OUT_GPKG = ROOT / "data" / "cloud_regions.gpkg"
LAYER = "regions"

REQUIRED_COLUMNS = {
    "provider",
    "region_code",
    "region_name",
    "location",
    "country",
    "latitude",
    "longitude",
}


def validate(df: pd.DataFrame) -> None:
    """Fail loud and early if the raw data is wrong. Cheap insurance."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")

    if df["region_code"].duplicated().any():
        dupes = df.loc[df["region_code"].duplicated(), "region_code"].tolist()
        raise ValueError(f"Duplicate region_code values: {dupes}")

    bad_lat = df.loc[~df["latitude"].between(-90, 90)]
    bad_lon = df.loc[~df["longitude"].between(-180, 180)]
    if len(bad_lat):
        raise ValueError(f"Latitude out of range for rows: {bad_lat.index.tolist()}")
    if len(bad_lon):
        raise ValueError(f"Longitude out of range for rows: {bad_lon.index.tolist()}")

    log.info("Validation passed: %d regions, %d providers",
             len(df), df["provider"].nunique())


def build_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Attach a point geometry to each row and tag it with the right CRS."""
    geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=WGS84)
    return gdf


def main() -> None:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Expected raw data at {RAW_CSV}")

    log.info("Reading %s", RAW_CSV)
    df = pd.read_csv(RAW_CSV)
    validate(df)

    gdf = build_geodataframe(df)
    gdf.to_file(OUT_GPKG, layer=LAYER, driver="GPKG")
    log.info("Wrote %d features to %s (layer=%s)", len(gdf), OUT_GPKG, LAYER)


if __name__ == "__main__":
    main()
