"""
CityGML I/O - Python Implementation

A Python re-implementation of the C++ CityGML reader.
Provides functionality to read CityGML files and export to various formats.
"""

__version__ = "1.0.0"
__author__ = "CityGML_IO Project"

from .gml_io import GMLReader
from .gml_mesh_component import MeshVertex, MeshFace, MeshFaceIndexed
from .geojson_io import GeoJSONWriter
from .obj_io import obj_writer, obj_writer_remap
from .obj_tri import face_normal, face_to_indexed_face, obj_face_earcut
from .json_io import face_to_json

__all__ = [
    'GMLReader',
    'MeshVertex',
    'MeshFace',
    'MeshFaceIndexed',
    'GeoJSONWriter',
    'obj_writer',
    'obj_writer_remap',
    'face_normal',
    'face_to_indexed_face',
    'obj_face_earcut',
    'face_to_json',
]
