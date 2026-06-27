"""
make_static_map.py

Render a world map of all cloud regions colored by provider and save it as a
PNG. This is the lightweight matplotlib path that runs without QGIS, so the
repo always has a picture in it. The PyQGIS version in export_maps.py is the
heavier, production style path.

The country outlines load from a public world GeoJSON. Swap the URL for a local
file if you would rather not hit the network.

Run:
    python src/make_static_map.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "cloud_regions.gpkg"
LAYER = "regions"
OUT_PNG = ROOT / "data" / "cloud_regions_map.png"

WORLD_GEOJSON = (
    "https://raw.githubusercontent.com/johan/world.geo.json/master/"
    "countries.geo.json"
)

PROVIDER_COLORS = {"AWS": "#ff9900", "GCP": "#4285f4", "Azure": "#008ad7"}


def main() -> None:
    if not GPKG.exists():
        raise FileNotFoundError(f"{GPKG} not found. Run load_regions.py first.")

    regions = gpd.read_file(GPKG, layer=LAYER)
    world = gpd.read_file(WORLD_GEOJSON)

    fig, ax = plt.subplots(figsize=(15, 7.5))
    world.plot(ax=ax, color="#e9ecef", edgecolor="#ced4da", linewidth=0.4)

    for provider, grp in regions.groupby("provider"):
        ax.scatter(
            grp.geometry.x, grp.geometry.y, s=70,
            c=PROVIDER_COLORS[provider], edgecolors="white",
            linewidths=0.8, label=provider, zorder=3,
        )

    ax.set_title("Multi-Cloud Regions: AWS, GCP, Azure", fontsize=16, pad=12)
    ax.set_xlim(-170, 180)
    ax.set_ylim(-60, 80)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(title="Provider", loc="lower left", frameon=True)
    ax.grid(True, linestyle=":", alpha=0.4)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    log.info("Wrote map to %s", OUT_PNG)


if __name__ == "__main__":
    main()
