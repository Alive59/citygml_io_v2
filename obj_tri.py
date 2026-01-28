"""
Object Triangulation Module - FIXED VERSION

This module provides polygon triangulation and mesh processing utilities.
FIXES:
- Proper 3D to 2D projection for triangulation
- Better fallback triangulation
- Memory efficiency improvements
"""

import math
from typing import List, Tuple, Optional
import numpy as np

try:
    from mapbox_earcut import triangulate_float32 as earcut_triangulate
except ImportError:
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

    if length > 1e-10:
        return (normal_vec[0] / length, normal_vec[1] / length, normal_vec[2] / length)
    else:
        return (0.0, 0.0, 1.0)


def create_local_coordinate_system(normal: Tuple[float, float, float]) -> Tuple[
    Tuple[float, float, float], 
    Tuple[float, float, float],
    Tuple[float, float, float]
]:
    """
    Create a local 2D coordinate system on a plane defined by a normal vector.
    
    Args:
        normal: Normal vector (nx, ny, nz)
    
    Returns:
        Tuple of (u_axis, v_axis, normal) forming an orthonormal basis
    """
    nx, ny, nz = normal
    
    # Find a vector that's not parallel to the normal
    if abs(nx) < 0.9:
        # Use X axis as reference
        ref = (1.0, 0.0, 0.0)
    else:
        # Use Y axis as reference
        ref = (0.0, 1.0, 0.0)
    
    # Compute u axis (perpendicular to normal)
    # u = ref × normal
    ux = ref[1] * nz - ref[2] * ny
    uy = ref[2] * nx - ref[0] * nz
    uz = ref[0] * ny - ref[1] * nx
    
    # Normalize u
    u_len = math.sqrt(ux**2 + uy**2 + uz**2)
    if u_len < 1e-10:
        # Fallback
        ux, uy, uz = 1.0, 0.0, 0.0
    else:
        ux /= u_len
        uy /= u_len
        uz /= u_len
    
    # Compute v axis = normal × u
    vx = ny * uz - nz * uy
    vy = nz * ux - nx * uz
    vz = nx * uy - ny * ux
    
    # Normalize v (should already be normalized, but just to be safe)
    v_len = math.sqrt(vx**2 + vy**2 + vz**2)
    if v_len > 1e-10:
        vx /= v_len
        vy /= v_len
        vz /= v_len
    
    return ((ux, uy, uz), (vx, vy, vz), normal)


def project_to_2d(vertices: List[MeshVertex], 
                  u_axis: Tuple[float, float, float],
                  v_axis: Tuple[float, float, float],
                  origin: Optional[MeshVertex] = None) -> List[Tuple[float, float]]:
    """
    Project 3D vertices onto a 2D plane defined by u and v axes.
    
    Args:
        vertices: List of 3D vertices
        u_axis: First axis of the 2D coordinate system
        v_axis: Second axis of the 2D coordinate system
        origin: Origin point for the projection (default: first vertex)
    
    Returns:
        List of 2D coordinates (u, v)
    """
    if not vertices:
        return []
    
    if origin is None:
        origin = vertices[0]
    
    vertices_2d = []
    for v in vertices:
        # Translate to origin
        dx = v.x - origin.x
        dy = v.y - origin.y
        dz = v.z - origin.z
        
        # Project onto u and v axes
        u = dx * u_axis[0] + dy * u_axis[1] + dz * u_axis[2]
        v_coord = dx * v_axis[0] + dy * v_axis[1] + dz * v_axis[2]
        
        vertices_2d.append((u, v_coord))
    
    return vertices_2d


def is_degenerate_face(face_indices: List[int]) -> bool:
    """
    Check if a face is degenerate (has duplicate vertex indices).

    A face is degenerate if any vertex index appears more than once,
    which creates invalid geometry (line segments or points instead of faces).

    Args:
        face_indices: List of vertex indices for a face

    Returns:
        True if face is degenerate, False otherwise
    """
    return len(face_indices) != len(set(face_indices))


def compute_polygon_area_2d(vertices_2d: List[Tuple[float, float]]) -> float:
    """
    Compute the signed area of a 2D polygon.
    
    Args:
        vertices_2d: List of 2D vertices
    
    Returns:
        Signed area (positive for CCW, negative for CW)
    """
    area = 0.0
    n = len(vertices_2d)
    for i in range(n):
        j = (i + 1) % n
        area += vertices_2d[i][0] * vertices_2d[j][1]
        area -= vertices_2d[j][0] * vertices_2d[i][1]
    return area * 0.5


def fallback_triangulation(num_vertices: int) -> List[int]:
    """
    Simple fan triangulation for convex polygons.
    Better than nothing, but only works correctly for convex polygons.
    
    Args:
        num_vertices: Number of vertices in the polygon
    
    Returns:
        List of triangle indices
    """
    if num_vertices < 3:
        return []
    
    indices = []
    for i in range(1, num_vertices - 1):
        indices.extend([0, i, i + 1])
    
    return indices


def face_to_indexed_face(mesh_group: List[MeshFace]) -> MeshFaceIndexed:
    """
    Remap triangularized mesh vertices to deduplicated indexed format.
    
    OPTIMIZED: Better memory usage and faster lookups.

    Args:
        mesh_group: List of MeshFace objects

    Returns:
        MeshFaceIndexed with deduplicated vertices (degenerate faces filtered)
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

        # Only add face if it's not degenerate
        if not is_degenerate_face(face_indices):
            result.faces.append(face_indices)
        # else:
        #     print(f"Warning: Skipped degenerate face with indices {face_indices}")

    return result


def obj_face_earcut(face: MeshFace) -> List[MeshFace]:
    """
    Triangulate a polygon face using earcut algorithm.
    
    FIXED: Now properly projects 3D polygons onto their plane before triangulation.

    Args:
        face: MeshFace object to triangulate

    Returns:
        List of triangulated MeshFace objects
    """
    face_vertices = face.face
    
    # Handle degenerate cases
    if len(face_vertices) < 3:
        return []
    
    if len(face_vertices) == 3:
        # Already a triangle
        return [face]
    
    # Calculate face normal
    f_normal = face_normal(face)
    
    # Create local 2D coordinate system on the polygon's plane
    u_axis, v_axis, normal = create_local_coordinate_system(f_normal)
    
    # Project vertices onto the 2D plane
    vertices_2d_tuples = project_to_2d(face_vertices, u_axis, v_axis)
    
    # Check if polygon is degenerate (zero area)
    area = compute_polygon_area_2d(vertices_2d_tuples)
    if abs(area) < 1e-10:
        # print(f"Warning: Degenerate polygon with near-zero area: {area}")
        return []
    
    # Flatten 2D vertices for earcut
    vertices_2d = []
    for u, v in vertices_2d_tuples:
        vertices_2d.extend([u, v])

    # Triangulate using earcut
    indices = None
    if earcut_triangulate is not None:
        try:
            # Convert to numpy array with float32 dtype as required by earcut
            # Reshape to (n_vertices, 2) format
            vertices_array = np.array(vertices_2d, dtype=np.float32).reshape(-1, 2)

            # Create rings array - for a simple polygon without holes,
            # it should contain the index where the outer ring ends
            num_vertices = len(vertices_2d_tuples)
            rings_array = np.array([num_vertices], dtype=np.uint32)

            # Call earcut with both required arguments
            indices = earcut_triangulate(vertices_array, rings_array)
        except Exception as e:
            print(f"Warning: Earcut triangulation failed: {e}, using fallback")
            indices = None
    
    if indices is None or len(indices) == 0:
        # Fallback to fan triangulation
        indices = fallback_triangulation(len(face_vertices))
        if not indices:
            return []
    
    # Create triangle faces using the original 3D vertices
    face_triangles = []
    for i in range(0, len(indices), 3):
        if i + 2 < len(indices):
            try:
                idx0 = indices[i]
                idx1 = indices[i + 1]
                idx2 = indices[i + 2]
                
                # Validate indices
                if idx0 >= len(face_vertices) or idx1 >= len(face_vertices) or idx2 >= len(face_vertices):
                    print(f"Warning: Invalid triangle indices {idx0}, {idx1}, {idx2} for {len(face_vertices)} vertices")
                    continue
                
                fvs = [
                    face_vertices[idx0],
                    face_vertices[idx1],
                    face_vertices[idx2]
                ]
                
                # Skip degenerate triangles
                if fvs[0] == fvs[1] or fvs[1] == fvs[2] or fvs[0] == fvs[2]:
                    continue
                
                f = MeshFace(face=fvs)
                
                # Check normal orientation against original face normal
                ft_normal = face_normal(f)
                dot_product = (f_normal[0] * ft_normal[0] +
                              f_normal[1] * ft_normal[1] +
                              f_normal[2] * ft_normal[2])
                
                # Reverse winding if normals point in opposite directions
                if dot_product < -0.5:  # Use threshold to avoid numerical issues
                    f.face.reverse()
                
                face_triangles.append(f)
            except (IndexError, ValueError) as e:
                print(f"Warning: Error creating triangle: {e}")
                continue
    
    return face_triangles
