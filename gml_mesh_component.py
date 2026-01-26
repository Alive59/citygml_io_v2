"""
GML Mesh Component Data Structures

This module provides data structures for representing 3D mesh geometry.
Equivalent to gml_mesh_component.h in C++ implementation.
"""

from dataclasses import dataclass
from typing import List
import math


@dataclass
class MeshVertex:
    """Represents a 3D vertex with x, y, z coordinates."""
    x: float
    y: float
    z: float

    EPSILON = 1e-9

    def __eq__(self, other):
        """Equality comparison with epsilon tolerance for floating point."""
        if not isinstance(other, MeshVertex):
            return False
        return (abs(self.x - other.x) < self.EPSILON and
                abs(self.y - other.y) < self.EPSILON and
                abs(self.z - other.z) < self.EPSILON)

    def __hash__(self):
        """Hash function for use in dictionaries/sets with epsilon tolerance."""
        x_rounded = int(self.x / self.EPSILON)
        y_rounded = int(self.y / self.EPSILON)
        z_rounded = int(self.z / self.EPSILON)
        return hash((x_rounded, y_rounded, z_rounded))

    def __str__(self):
        return f"{self.x} {self.y} {self.z}"

    def __repr__(self):
        return f"MeshVertex({self.x}, {self.y}, {self.z})"


@dataclass
class MeshFace:
    """Represents a polygonal face as a list of vertices."""
    face: List[MeshVertex]

    def __str__(self):
        return ' '.join(str(v) for v in self.face)


@dataclass
class MeshFaceIndexed:
    """
    Represents mesh with deduplicated vertices and indexed faces.

    Attributes:
        vertices: List of unique vertices
        faces: List of face indices (each face is a list of vertex indices)
    """
    vertices: List[MeshVertex]
    faces: List[List[int]]
