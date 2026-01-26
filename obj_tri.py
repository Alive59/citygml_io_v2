"""
Object Triangulation Module

This module provides polygon triangulation and mesh processing utilities.
Equivalent to obj_tri.h in C++ implementation.
"""

import math
from typing import List, Tuple
try:
    from mapbox_earcut import triangulate_float32 as earcut_triangulate
except ImportError:
    # Fallback if mapbox_earcut is not available
    earcut_triangulate = None

from gml_mesh_component import MeshVertex, MeshFace, MeshFaceIndexed


def face_normal(face: MeshFace) -> Tuple[float, float, float]:
    """
    Calculate the normal vector of a polygon using Newell's method.

    Args:
        face: MeshFace object

    Returns:
        Normalized normal vector (nx, ny, nz)
    """
    normal_vec = [0.0, 0.0, 0.0]
    vertices = face.face
    num_vertices = len(vertices)

    for idx in range(num_vertices):
        current = vertices[idx]
        next_v = vertices[(idx + 1) % num_vertices]

        normal_vec[0] += (current.y - next_v.y) * (current.z + next_v.z)
        normal_vec[1] += (current.z - next_v.z) * (current.x + next_v.x)
        normal_vec[2] += (current.x - next_v.x) * (current.y + next_v.y)

    length = math.sqrt(normal_vec[0] ** 2 + normal_vec[1] ** 2 + normal_vec[2] ** 2)

    if length > 0:
        return (normal_vec[0] / length, normal_vec[1] / length, normal_vec[2] / length)
    else:
        return (0.0, 0.0, 1.0)


def face_to_indexed_face(mesh_group: List[MeshFace]) -> MeshFaceIndexed:
    """
    Remap triangularized mesh vertices to deduplicated indexed format.

    Args:
        mesh_group: List of MeshFace objects

    Returns:
        MeshFaceIndexed with deduplicated vertices
    """
    result = MeshFaceIndexed(vertices=[], faces=[])
    vertex_to_index_map = {}

    for face in mesh_group:
        face_indices = []
        for vertex in face.face:
            # Check if vertex already exists
            if vertex in vertex_to_index_map:
                face_indices.append(vertex_to_index_map[vertex])
            else:
                # Add new vertex
                new_idx = len(result.vertices)
                vertex_to_index_map[vertex] = new_idx
                face_indices.append(new_idx)
                result.vertices.append(vertex)

        result.faces.append(face_indices)

    return result


def obj_face_earcut(face: MeshFace) -> List[MeshFace]:
    """
    Triangulate a polygon face using earcut algorithm.

    Args:
        face: MeshFace object to triangulate

    Returns:
        List of triangulated MeshFace objects
    """
    face_vertices = face.face

    # Calculate original face normal
    f_normal = face_normal(face)

    # Prepare vertices for earcut (2D coordinates)
    vertices_2d = []
    for vertex in face.face:
        vertices_2d.extend([vertex.x, vertex.y])

    # Triangulate using earcut
    if earcut_triangulate is not None:
        try:
            indices = earcut_triangulate(vertices_2d, rings=None, dim=2)
        except Exception as e:
            print(f"Earcut triangulation failed: {e}")
            # Return original face as fallback
            return [face]
    else:
        # Fallback: simple fan triangulation for convex polygons
        indices = []
        for i in range(1, len(face_vertices) - 1):
            indices.extend([0, i, i + 1])

    # Create triangle faces
    face_triangles = []
    for i in range(0, len(indices), 3):
        if i + 2 < len(indices):
            fvs = [
                face_vertices[indices[i]],
                face_vertices[indices[i + 1]],
                face_vertices[indices[i + 2]]
            ]
            f = MeshFace(face=fvs)

            # Check normal orientation
            ft_normal = face_normal(f)
            dot_product = (f_normal[0] * ft_normal[0] +
                          f_normal[1] * ft_normal[1] +
                          f_normal[2] * ft_normal[2])

            # Reverse winding if normals point in opposite directions
            if dot_product < 0:
                f.face.reverse()

            face_triangles.append(f)

    return face_triangles
