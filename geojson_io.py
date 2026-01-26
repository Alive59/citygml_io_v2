"""
GeoJSON Writer Module

This module provides functionality to write GeoJSON files.
Equivalent to geojson_io.h in C++ implementation.
"""

import json
from typing import List, Dict, Any

from gml_mesh_component import MeshFace


class GeoJSONWriter:
    """Writer for GeoJSON format with support for MultiPolygon features."""

    def __init__(self):
        """Initialize GeoJSON writer."""
        self.features: List[Dict[str, Any]] = []
        self.crs: Dict[str, Any] = {}

    def add_multi_polygon(self, mesh: List[MeshFace],
                         properties: Dict[str, Any] = None):
        """
        Add a MultiPolygon feature.

        Args:
            mesh: List of MeshFace objects representing polygons
            properties: Dictionary of feature properties (e.g., id, height)
        """
        if properties is None:
            properties = {}

        polygons = []

        for mesh_obj in mesh:
            coords = []
            for vertex in mesh_obj.face:
                coords.append([vertex.x, vertex.y])

            # Close the polygon by adding first vertex at the end
            if mesh_obj.face:
                coords.append([mesh_obj.face[0].x, mesh_obj.face[0].y])

            polygons.append(coords)

        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [polygons]
            }
        }

        self.features.append(feature)

    def set_crs(self, code: str, crs_type: str = "OGC"):
        """
        Set coordinate reference system.

        Args:
            code: CRS code (e.g., "EPSG:30169")
            crs_type: Type of CRS ("OGC" or "EPSG")
        """
        if crs_type == "OGC":
            self.crs = {
                "type": "name",
                "properties": {
                    "name": f"urn:ogc:def:crs:{code}"
                }
            }
        elif crs_type == "EPSG":
            self.crs = {
                "type": "name",
                "properties": {
                    "name": f"EPSG:{code}"
                }
            }
        else:
            raise ValueError(f"Not implemented type: {crs_type}")

    def write(self, filename: str):
        """
        Write GeoJSON to file.

        Args:
            filename: Output file path
        """
        geojson = {
            "type": "FeatureCollection",
            "crs": self.crs,
            "features": self.features
        }

        with open(filename, 'w') as f:
            json.dump(geojson, f, indent=2)
