#!/usr/bin/env python3
"""
CityGML I/O Main Program - OPTIMIZED VERSION

IMPROVEMENTS:
- Better memory management with explicit cleanup
- Progress reporting for large datasets
- Batch processing to reduce memory footprint
- Error handling and validation
- Performance metrics
"""

import os
import sys
import time
import json
import gc
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


def process_single_object(reader: GMLReader, object_idx: int, 
                          transformer, lod_number: int, 
                          earcut: bool, valid_pass: bool,
                          obj_dir: Path = None,
                          geojson_writer: GeoJSONWriter = None,
                          all_data: list = None) -> dict:
    """
    Process a single object with memory cleanup.
    
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        'triangles': 0,
        'vertices': 0,
        'skipped': False,
        'error': None
    }
    
    try:
        # Check if object has the required LOD
        if not reader.check_object_member_lod(object_idx, lod_number):
            stats['skipped'] = True
            return stats

        object_gml_id = reader.get_object_id(object_idx)
        measured_height = reader.get_object_measured_height(object_idx)

        # Convert pos list to vertices
        obj_mesh = []
        reader.gml_polygon_converter(object_idx, obj_mesh)

        if not valid_pass:
            reader.object_filter_update(object_idx)

        obj_mesh_proj = []
        
        for mesh_idx in range(len(obj_mesh)):
            if not (reader.get_object_mesh_filtering(object_idx, mesh_idx) or valid_pass):
                continue

            mesh_proj = []
            
            # Apply coordinate transformation
            for v in obj_mesh[mesh_idx]:
                if transformer is not None:
                    try:
                        x_proj, y_proj = transformer.transform(v.y, v.x)
                        mesh_proj.append(MeshVertex(x_proj, y_proj, v.z))
                    except Exception as e:
                        # Fallback to original coordinates on transformation error
                        mesh_proj.append(MeshVertex(v.x, v.y, v.z))
                else:
                    mesh_proj.append(MeshVertex(v.x, v.y, v.z))

            # Create mesh face
            if not mesh_proj:
                continue
                
            mf = MeshFace(face=mesh_proj)

            if earcut and lod_number > 0:
                # Triangulate the face
                mf_tri = obj_face_earcut(mf)
                obj_mesh_proj.extend(mf_tri)
                stats['triangles'] += len(mf_tri)
            else:
                obj_mesh_proj.append(mf)

        # Clear intermediate data
        obj_mesh.clear()
        del obj_mesh

        # Convert to indexed face format for OBJ output
        if obj_mesh_proj:
            obj_mesh_proj_remapped = face_to_indexed_face(obj_mesh_proj)
            stats['vertices'] = len(obj_mesh_proj_remapped.vertices)

            # Write OBJ file
            if obj_dir is not None:
                output_path = obj_dir / f"{object_gml_id}.obj"
                with open(output_path, 'w') as obj_out:
                    obj_writer_remap(obj_out, obj_mesh_proj_remapped)

            # Add to JSON if requested
            if all_data is not None:
                face_to_json(all_data, object_gml_id, obj_mesh_proj_remapped)

            # Add to GeoJSON
            if geojson_writer is not None and lod_number == 0:
                geojson_writer.add_multi_polygon(
                    obj_mesh_proj,
                    {
                        "id": object_gml_id,
                        "height": measured_height
                    }
                )
            
            # Clear memory
            obj_mesh_proj.clear()
            del obj_mesh_proj
            del obj_mesh_proj_remapped
        
    except Exception as e:
        stats['error'] = str(e)
        print(f"Error processing object {object_idx}: {e}")
    
    return stats


def main():
    """Main program entry point with optimizations."""
    time_start = time.time()

    # Configuration
    gml_tile_id = "53394632"

    print("=" * 60)
    print("CityGML to OBJ Converter - OPTIMIZED VERSION")
    print("=" * 60)

    # File paths
    root_dir = Path("/Users/konialive/Documents/vs_codes/plateauGML/GML_IO_v2/data_fortest/")
    gml_file_path = f"{gml_tile_id}_bldg_6697_op.gml"
    path = root_dir / gml_file_path
    gml_path = str(path)

    # Check if file exists
    if not os.path.exists(gml_path):
        print(f"ERROR: {gml_path} not found.")
        print("Please adjust the path in the script.")
        sys.exit(1)

    # Read GML file
    lod_number = 2
    lod2_face_filter = ""
    valid_pass = lod2_face_filter == "" or lod_number < 2

    print(f"\n[1/4] Reading GML file: {gml_path}")
    print(f"      LOD Level: {lod_number}")
    
    reader = GMLReader(gml_path, lod_number)
    reader.gml_object_reader(lod2_face_filter)
    
    num_objects = reader.get_object_num()
    print(f"      Found {num_objects} objects")

    # Set up coordinate transformation
    src_crs = "EPSG:6697"
    tgt_crs = "EPSG:30169"

    transformer = None
    if Transformer is not None:
        try:
            print(f"\n[2/4] Setting up coordinate transformation")
            print(f"      {src_crs} -> {tgt_crs}")
            transformer = Transformer.from_crs(src_crs, tgt_crs, always_xy=True)
        except Exception as e:
            print(f"      Warning: Could not create transformer: {e}")

    # Output configuration
    is_geojson_available = lod_number == 0
    is_obj_available = lod_number >= 1
    is_json_available = False
    earcut = True

    print(f"\n[3/4] Output configuration")
    print(f"      OBJ output: {is_obj_available}")
    print(f"      GeoJSON output: {is_geojson_available}")
    print(f"      Triangulation: {earcut}")

    # Initialize GeoJSON writer
    geojson_writer = None
    if is_geojson_available:
        geojson_writer = GeoJSONWriter()
        geojson_writer.set_crs(tgt_crs)

    # Create output directory for OBJ files
    obj_dir = None
    if is_obj_available:
        obj_dir = Path("obj") / gml_tile_id
        obj_dir.mkdir(parents=True, exist_ok=True)
        print(f"      OBJ directory: {obj_dir}")

    all_data = [] if is_json_available else None

    # Process each object with progress reporting
    print(f"\n[4/4] Processing objects...")
    
    total_triangles = 0
    total_vertices = 0
    objects_processed = 0
    objects_skipped = 0
    errors = []
    
    report_interval = max(1, num_objects // 20)  # Report every 5%
    
    for object_idx in range(num_objects):
        # Progress reporting
        if object_idx % report_interval == 0 or object_idx == num_objects - 1:
            progress = (object_idx + 1) / num_objects * 100
            print(f"      Progress: {progress:.1f}% ({object_idx + 1}/{num_objects})")
        
        stats = process_single_object(
            reader, object_idx, transformer, lod_number,
            earcut, valid_pass, obj_dir, geojson_writer, all_data
        )
        
        if stats['skipped']:
            objects_skipped += 1
        elif stats['error']:
            errors.append((object_idx, stats['error']))
        else:
            objects_processed += 1
            total_triangles += stats['triangles']
            total_vertices += stats['vertices']
        
        # Periodic garbage collection for large datasets
        if object_idx % 100 == 0:
            gc.collect()

    # Write JSON output
    if is_json_available and all_data:
        output_json_path = Path("../json") / f"{gml_tile_id}_sample.json"
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, 'w') as json_out:
            json.dump(all_data, json_out, indent=4)
        print(f"\n      JSON written to: {output_json_path}")

    # Write GeoJSON output
    if is_geojson_available and geojson_writer:
        output_geojson_path = Path("test_geojson") / f"{gml_tile_id}.geojson"
        output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
        geojson_writer.write(str(output_geojson_path))
        print(f"\n      GeoJSON written to: {output_geojson_path}")

    # Final cleanup
    del reader
    gc.collect()

    time_end = time.time()
    time_elapsed = time_end - time_start

    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Time elapsed:        {time_elapsed:.3f} seconds")
    print(f"Objects processed:   {objects_processed}")
    print(f"Objects skipped:     {objects_skipped}")
    print(f"Total triangles:     {total_triangles}")
    print(f"Total vertices:      {total_vertices}")
    
    if total_triangles > 0:
        print(f"Avg triangles/obj:   {total_triangles / max(1, objects_processed):.1f}")
        print(f"Performance:         {objects_processed / time_elapsed:.1f} objects/sec")
    
    if errors:
        print(f"\nErrors encountered:  {len(errors)}")
        for idx, error in errors[:5]:  # Show first 5 errors
            print(f"  Object {idx}: {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
