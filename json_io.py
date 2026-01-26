"""
JSON Writer Module

This module provides functionality to write custom JSON format.
Equivalent to json_io.h in C++ implementation.
"""

from typing import List

from gml_mesh_component import MeshFaceIndexed


def face_to_json(all_data: List[dict], object_id: str, mesh: MeshFaceIndexed):
    """
    Convert mesh faces to JSON format and append to data list.

    Args:
        all_data: List to append face data to
        object_id: Object identifier
        mesh: MeshFaceIndexed object with vertices and faces
    """
    for face in mesh.faces:
        face_vertices = []

        for vidx in face:
            if 0 <= vidx < len(mesh.vertices):
                vertex = mesh.vertices[vidx]
                face_vertices.append([vertex.x, vertex.y, vertex.z])
            else:
                print(f"Invalid vertex index {vidx}")

        all_data.append({
            "ID": object_id,
            "Face": face_vertices
        })
