"""
postgis_loader.py

Push the regions into a PostGIS table so the heavy spatial queries can run in
the database instead of in Python. This is the part that shows you understand
where spatial work belongs at scale: in an indexed database, not a script.

Connection settings come from environment variables so no secrets live in code:
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

Run:
    python src/postgis_loader.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import geopandas as gpd
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "cloud_regions.gpkg"
LAYER = "regions"
TABLE = "cloud_regions"


def build_engine():
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    db = os.environ.get("PGDATABASE", "geo")
    user = os.environ.get("PGUSER", "postgres")
    pw = os.environ.get("PGPASSWORD", "")
    url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
    return create_engine(url)


def main() -> None:
    if not GPKG.exists():
        raise FileNotFoundError(f"{GPKG} not found. Run load_regions.py first.")

    gdf = gpd.read_file(GPKG, layer=LAYER)
    engine = build_engine()

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    # GeoPandas writes the geometry column and registers the SRID for us.
    gdf.to_postgis(TABLE, engine, if_exists="replace", index=False)
    log.info("Loaded %d rows into table %s", len(gdf), TABLE)

    # A spatial index is the whole point of using PostGIS. Without it, nearest
    # neighbor and radius queries do a full table scan.
    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS {TABLE}_geom_idx "
            f"ON {TABLE} USING GIST (geometry);"
        ))
    log.info("Created GIST spatial index on %s.geometry", TABLE)


if __name__ == "__main__":
    main()
