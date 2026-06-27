"""
spatial_analysis.py

The actual analysis. Four questions a cloud team genuinely asks:

1. Nearest region. Given a customer location, which region is closest and how far?
2. Pairwise distances. How far is every region from every other region?
   This is a proxy for replication latency between regions.
3. Coverage. How many regions sit within a chosen radius of a major city?
4. Per provider spread. Where is each provider's center of mass and how wide
   is its footprint?

All distances are true geodesic distances on the WGS84 globe, in kilometers.
We use pyproj.Geod, not flat planar math, because the regions span the whole
planet and flat math would be wrong at that scale.

Run:
    python src/spatial_analysis.py --customer-lat 32.72 --customer-lon -117.16
"""

from __future__ import annotations

import argparse
import logging
from itertools import combinations
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import Geod

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "cloud_regions.gpkg"
LAYER = "regions"
OUT_DIR = ROOT / "data"

# WGS84 ellipsoid. Geodesic math respects the real shape of the Earth.
GEOD = Geod(ellps="WGS84")

# A few major demand centers for the coverage question.
CITIES = {
    "San Diego": (32.72, -117.16),
    "London": (51.51, -0.13),
    "Singapore": (1.35, 103.82),
    "Sao Paulo": (-23.55, -46.63),
}


def geodesic_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great circle distance on the WGS84 ellipsoid, in kilometers."""
    _, _, meters = GEOD.inv(lon1, lat1, lon2, lat2)
    return meters / 1000.0


def load() -> gpd.GeoDataFrame:
    if not GPKG.exists():
        raise FileNotFoundError(
            f"{GPKG} not found. Run load_regions.py first."
        )
    return gpd.read_file(GPKG, layer=LAYER)


def nearest_region(gdf: gpd.GeoDataFrame, lat: float, lon: float) -> pd.Series:
    """Return the single closest region to a point, with the distance attached."""
    dist = gdf.apply(
        lambda r: geodesic_km(lat, lon, r.geometry.y, r.geometry.x), axis=1
    )
    out = gdf.copy()
    out["distance_km"] = dist.round(1)
    return out.sort_values("distance_km").iloc[0]


def pairwise_distances(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Every region to every other region. Useful as a latency proxy matrix."""
    rows = []
    for a, b in combinations(gdf.itertuples(index=False), 2):
        rows.append(
            {
                "region_a": a.region_code,
                "region_b": b.region_code,
                "provider_a": a.provider,
                "provider_b": b.provider,
                "distance_km": round(
                    geodesic_km(a.geometry.y, a.geometry.x,
                                b.geometry.y, b.geometry.x), 1
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("distance_km").reset_index(drop=True)


def coverage(gdf: gpd.GeoDataFrame, radius_km: float) -> pd.DataFrame:
    """For each city, count regions within radius_km and list the closest."""
    rows = []
    for city, (lat, lon) in CITIES.items():
        d = gdf.apply(
            lambda r: geodesic_km(lat, lon, r.geometry.y, r.geometry.x), axis=1
        )
        within = gdf.loc[d <= radius_km].copy()
        within["distance_km"] = d.loc[within.index].round(1)
        closest = within.sort_values("distance_km")
        rows.append(
            {
                "city": city,
                "regions_within_radius": len(within),
                "closest_region": (
                    closest.iloc[0]["region_code"] if len(closest) else None
                ),
                "closest_km": (
                    closest.iloc[0]["distance_km"] if len(closest) else None
                ),
            }
        )
    return pd.DataFrame(rows)


def provider_spread(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Center of mass per provider and how far the farthest region sits from it."""
    rows = []
    for provider, grp in gdf.groupby("provider"):
        clat = grp.geometry.y.mean()
        clon = grp.geometry.x.mean()
        max_km = grp.apply(
            lambda r: geodesic_km(clat, clon, r.geometry.y, r.geometry.x), axis=1
        ).max()
        rows.append(
            {
                "provider": provider,
                "region_count": len(grp),
                "centroid_lat": round(clat, 3),
                "centroid_lon": round(clon, 3),
                "max_spread_km": round(max_km, 1),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Multi-cloud region spatial analysis")
    ap.add_argument("--customer-lat", type=float, default=32.72,
                    help="Customer latitude (default: San Diego)")
    ap.add_argument("--customer-lon", type=float, default=-117.16,
                    help="Customer longitude (default: San Diego)")
    ap.add_argument("--radius-km", type=float, default=2000.0,
                    help="Coverage radius in km (default: 2000)")
    args = ap.parse_args()

    gdf = load()

    near = nearest_region(gdf, args.customer_lat, args.customer_lon)
    log.info("Nearest region to (%.2f, %.2f): %s [%s] at %.1f km",
             args.customer_lat, args.customer_lon,
             near["region_code"], near["provider"], near["distance_km"])

    pairs = pairwise_distances(gdf)
    pairs.to_csv(OUT_DIR / "pairwise_distances.csv", index=False)
    log.info("Wrote pairwise distance matrix (%d pairs). Closest two regions:",
             len(pairs))
    log.info("  %s <-> %s : %.1f km",
             pairs.iloc[0]["region_a"], pairs.iloc[0]["region_b"],
             pairs.iloc[0]["distance_km"])

    cov = coverage(gdf, args.radius_km)
    cov.to_csv(OUT_DIR / "coverage.csv", index=False)
    log.info("Coverage within %.0f km:\n%s", args.radius_km, cov.to_string(index=False))

    spread = provider_spread(gdf)
    spread.to_csv(OUT_DIR / "provider_spread.csv", index=False)
    log.info("Provider spread:\n%s", spread.to_string(index=False))


if __name__ == "__main__":
    main()
