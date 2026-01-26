"""
OBJ Writer Module

This module provides functionality to write OBJ (Wavefront) format files.
Equivalent to obj_io.h in C++ implementation.
"""

from typing import List, TextIO

from gml_mesh_component import MeshFace, MeshFaceIndexed


def obj_writer(obj_out: TextIO, faces: List[MeshFace]):
    """
    Write mesh faces to OBJ file (non-indexed version).

    Args:
        obj_out: Output file object
        faces: List of MeshFace objects
    """
    # Write vertices
    for face in faces:
        for vertex in face.face:
            obj_out.write(f"v {vertex.x:.12f} {vertex.y:.12f} {vertex.z:.12f}\n")

    # Write faces
    vertex_num = 0
    for face in faces:
        obj_out.write("f")
        for i in range(1, len(face.face) + 1):
            obj_out.write(f" {vertex_num + i}")
        obj_out.write("\n")
        vertex_num += len(face.face)


def obj_writer_remap(obj_out: TextIO, faces: MeshFaceIndexed):
    """
    Write indexed mesh to OBJ file (deduplicated vertices).

    Args:
        obj_out: Output file object
        faces: MeshFaceIndexed object with deduplicated vertices
    """
    # Write vertices
    for vertex in faces.vertices:
        obj_out.write(f"v {vertex.x:.12f} {vertex.y:.12f} {vertex.z:.12f}\n")

    # Write faces with indices (OBJ uses 1-based indexing)
    for face in faces.faces:
        obj_out.write("f")
        for idx in face:
            obj_out.write(f" {idx + 1}")
        obj_out.write("\n")
