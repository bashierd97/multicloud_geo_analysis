"""
export_maps.py

A PyQGIS script that loads the regions layer, colors the points by cloud
provider, and exports a finished PNG map with no human clicking anything.
This is the piece that proves the QGIS part of the project is automation, not
GUI work.

It runs inside the QGIS Python environment, not plain python. Two ways to run:

1. QGIS GUI: Plugins > Python Console > Show Editor > open and run this file.
2. Headless from a terminal that has QGIS on its path:
       qgis_process run script --script=src/export_maps.py
   or call it through the standalone PyQGIS app launcher.

The import lines below only resolve when QGIS is present. That is expected.
"""

from __future__ import annotations

import os
from pathlib import Path

from qgis.core import (
    QgsApplication,
    QgsVectorLayer,
    QgsProject,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsMarkerSymbol,
    QgsLayoutExporter,
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutSize,
    QgsUnitTypes,
)
from qgis.PyQt.QtGui import QColor

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "data" / "cloud_regions.gpkg"
LAYER = "regions"
OUT_PNG = ROOT / "data" / "cloud_regions_map.png"

PROVIDER_COLORS = {
    "AWS": "#ff9900",
    "GCP": "#4285f4",
    "Azure": "#008ad7",
}


def load_layer() -> QgsVectorLayer:
    uri = f"{GPKG}|layername={LAYER}"
    layer = QgsVectorLayer(uri, "Cloud Regions", "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Failed to load layer from {uri}")
    return layer


def style_by_provider(layer: QgsVectorLayer) -> None:
    """Color each point by its provider using a categorized renderer."""
    categories = []
    for provider, hex_color in PROVIDER_COLORS.items():
        symbol = QgsMarkerSymbol.createSimple(
            {"name": "circle", "size": "4", "color": hex_color}
        )
        categories.append(QgsRendererCategory(provider, symbol, provider))
    renderer = QgsCategorizedSymbolRenderer("provider", categories)
    layer.setRenderer(renderer)
    layer.triggerRepaint()


def export_png(project: QgsProject, layer: QgsVectorLayer) -> None:
    """Build a one page layout, frame the layer, and write a PNG."""
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()

    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(0, 0, 297, 210)  # A4 landscape millimeters
    map_item.setExtent(layer.extent())
    layout.addLayoutItem(map_item)
    map_item.attemptResize(QgsLayoutSize(297, 210, QgsUnitTypes.LayoutMillimeters))

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 200
    result = exporter.exportToImage(str(OUT_PNG), settings)
    if result != QgsLayoutExporter.Success:
        raise RuntimeError(f"Export failed with code {result}")
    print(f"Wrote map to {OUT_PNG}")


def run() -> None:
    project = QgsProject.instance()
    layer = load_layer()
    style_by_provider(layer)
    project.addMapLayer(layer)
    export_png(project, layer)


# When run as a standalone script (not inside the GUI), boot QGIS first.
if __name__ == "__main__":
    qgis_prefix = os.environ.get("QGIS_PREFIX_PATH", "/usr")
    QgsApplication.setPrefixPath(qgis_prefix, True)
    app = QgsApplication([], False)
    app.initQgis()
    try:
        run()
    finally:
        app.exitQgis()
