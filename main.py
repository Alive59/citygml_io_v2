#!/usr/bin/env python3
"""
CityGML I/O Main Program

This program reads CityGML files, converts building geometry data,
performs coordinate transformations, and exports to OBJ/GeoJSON formats.

This is a Python re-implementation of the C++ main.cpp program.
"""

import os
import sys
import time
import json
from pathlib import Path

try:
    from pyproj import Transformer
except ImportError:
    print("Warning: pyproj not available. Coordinate transformation will be skipped.")
    Transformer = None

from gml_io import GMLReader
from geojson_io import GeoJSONWriter
from obj_io import obj_writer_remap
from obj_tri import obj_face_earcut, face_to_indexed_face
from json_io import face_to_json
from gml_mesh_component import MeshVertex, MeshFace


def main():
    """Main program entry point."""
    time_start = time.time()

    # Configuration
    gml_tile_id = "53395528"

    print("I/O TEST")

    # File paths (adjust these paths as needed)
    root_dir = Path("/Users/konialive/Downloads/13117_kita-ku_city_2023_citygml_1_op/udx/bldg")
    gml_file_path = f"{gml_tile_id}_bldg_6697_op.gml"
    path = root_dir / gml_file_path
    gml_path = str(path)

    # Check if file exists, otherwise use a relative path for testing
    if not os.path.exists(gml_path):
        print(f"Warning: {gml_path} not found. Please adjust the path.")
        print("You can modify the root_dir and gml_file_path variables in main.py")
        # Example: use current directory
        # gml_path = "sample.gml"

    # Read GML file
    lod_number = 0
    lod2_face_filter = ""  # e.g., "bldg:WallSurface"
    valid_pass = lod2_face_filter == "" or lod_number < 2

    print(f"Reading GML file: {gml_path}")
    reader = GMLReader(gml_path, lod_number)
    reader.gml_object_reader(lod2_face_filter)

    # Set up coordinate transformation
    src_crs = "EPSG:6697"
    tgt_crs = "EPSG:30169"

    transformer = None
    if Transformer is not None:
        try:
            transformer = Transformer.from_crs(src_crs, tgt_crs, always_xy=True)
        except Exception as e:
            print(f"Warning: Could not create coordinate transformer: {e}")

    # Output configuration
    is_geojson_available = lod_number == 0
    is_obj_available = lod_number >= 1
    is_json_available = False
    earcut = True

    # Initialize GeoJSON writer
    geojson_writer = GeoJSONWriter()
    geojson_writer.set_crs(tgt_crs)

    # Create output directory for OBJ files
    obj_dir = Path("../obj") / gml_tile_id
    if lod_number >= 2:
        obj_dir.mkdir(parents=True, exist_ok=True)

    all_data = []

    # Process each object
    num_objects = reader.get_object_num()
    print(f"Processing {num_objects} objects...")

    for object_idx in range(num_objects):
        is_ground_truth = False

        # Check if object has the required LOD
        if not reader.check_object_member_lod(object_idx, lod_number):
            continue

        if not is_ground_truth and reader.check_object_member_lod(object_idx, lod_number):
            is_ground_truth = True

        object_gml_id = reader.get_object_id(object_idx)
        measured_height = reader.get_object_measured_height(object_idx)

        # Convert pos list to vertices
        obj_mesh = []
        obj_mesh_proj = []
        reader.gml_polygon_converter(object_idx, obj_mesh)

        if not valid_pass:
            reader.object_filter_update(object_idx)

        for mesh_idx in range(len(obj_mesh)):
            mesh_proj = []

            if not (reader.get_object_mesh_filtering(object_idx, mesh_idx) or valid_pass):
                continue

            # Apply coordinate transformation
            for v in obj_mesh[mesh_idx]:
                if transformer is not None:
                    try:
                        # Transform coordinates
                        x_proj, y_proj = transformer.transform(v.y, v.x)
                        # Note: swapping x and y to match C++ behavior
                        mesh_proj.append(MeshVertex(x_proj, y_proj, v.z))
                    except Exception as e:
                        print(f"Warning: Transformation failed for vertex: {e}")
                        mesh_proj.append(MeshVertex(v.x, v.y, v.z))
                else:
                    # No transformation available
                    mesh_proj.append(MeshVertex(v.x, v.y, v.z))

            # Create mesh face
            mf = MeshFace(face=mesh_proj)

            if earcut:
                if lod_number == 0:
                    obj_mesh_proj.append(mf)
                else:
                    # Triangulate the face
                    mf_tri = obj_face_earcut(mf)
                    obj_mesh_proj.extend(mf_tri)
            else:
                obj_mesh_proj.append(mf)

        # Convert to indexed face format for OBJ output
        if is_obj_available and obj_mesh_proj:
            obj_mesh_proj_remapped = face_to_indexed_face(obj_mesh_proj)

            if is_ground_truth:
                output_path = obj_dir / f"{object_gml_id}.obj"
                with open(output_path, 'w') as obj_out:
                    obj_writer_remap(obj_out, obj_mesh_proj_remapped)

            if is_json_available:
                face_to_json(all_data, object_gml_id, obj_mesh_proj_remapped)

        # Add to GeoJSON
        if is_geojson_available and obj_mesh_proj:
            geojson_writer.add_multi_polygon(
                obj_mesh_proj,
                {
                    "id": object_gml_id,
                    "height": measured_height
                }
            )

    # Write JSON output
    if is_json_available and all_data:
        output_json_path = Path("../json") / f"{gml_tile_id}_sample.json"
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, 'w') as json_out:
            json.dump(all_data, json_out, indent=4)

    # Write GeoJSON output
    if is_geojson_available:
        output_geojson_path = Path("../test_geojson") / f"{gml_tile_id}.geojson"
        output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
        geojson_writer.write(str(output_geojson_path))
        print(f"GeoJSON written to: {output_geojson_path}")

    time_end = time.time()
    time_elapsed = time_end - time_start
    print(f"Converted meshes in {time_elapsed:.3f} seconds.")


if __name__ == "__main__":
    main()
