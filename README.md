# CityGML I/O - Python Implementation

This directory contains a Python re-implementation of the CityGML reader functionality originally written in C++.

## Overview

This Python implementation provides the same core functionality as the C++ version:
- Reading CityGML 2.0 files
- Extracting building geometry with LOD (Level of Detail) support
- Coordinate transformation between different CRS (Coordinate Reference Systems)
- Exporting to multiple formats: OBJ, GeoJSON, and custom JSON

## Features

- **Efficient XML Parsing**: Uses Python's built-in `xml.etree.ElementTree` (C implementation)
- **Coordinate Transformation**: Uses `pyproj` (Python bindings to PROJ library)
- **Polygon Triangulation**: Uses `mapbox_earcut` for efficient polygon triangulation
- **Multiple Output Formats**:
  - OBJ (Wavefront) format for 3D models
  - GeoJSON for web/GIS applications
  - Custom JSON format for face data

## File Structure

```
gml_io_py/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── main.py                      # Main program (equivalent to main.cpp)
├── gml_io.py                   # GML reader (equivalent to gml_io.h)
├── gml_mesh_component.py       # Data structures (equivalent to gml_mesh_component.h)
├── geojson_io.py               # GeoJSON writer (equivalent to geojson_io.h)
├── obj_io.py                   # OBJ writer (equivalent to obj_io.h)
├── obj_tri.py                  # Triangulation (equivalent to obj_tri.h)
└── json_io.py                  # JSON writer (equivalent to json_io.h)
```

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Required packages**:
   - `pyproj>=3.0.0`: For coordinate transformation
   - `mapbox_earcut>=1.0.0`: For polygon triangulation

## Usage

### Basic Usage

```bash
cd gml_io_py
python main.py
```

### Customizing Paths

Edit `main.py` to configure:
- `gml_tile_id`: Tile identifier
- `root_dir`: Directory containing GML files
- `gml_file_path`: GML file name
- `lod_number`: Level of Detail (0-3)

Example:
```python
gml_tile_id = "52354611"
root_dir = Path("/path/to/your/gml/files")
gml_file_path = f"{gml_tile_id}_bldg_6697_op.gml"
lod_number = 0  # Change LOD level
```

### Using as a Library

```python
from gml_io import GMLReader
from geojson_io import GeoJSONWriter

# Read GML file
reader = GMLReader("path/to/file.gml", lod_number=0)
reader.gml_object_reader()

# Create GeoJSON writer
writer = GeoJSONWriter()
writer.set_crs("EPSG:30169")

# Process objects...
# (see main.py for complete example)
```

## Performance Considerations

This Python implementation is designed with efficiency in mind:

1. **XML Parsing**: Uses `xml.etree.ElementTree`, which has a C implementation (cElementTree) for fast parsing
2. **Data Structures**: Uses efficient built-in types and minimal copying
3. **Coordinate Transformation**: Uses `pyproj` which is a thin wrapper around the PROJ C library
4. **Triangulation**: Uses `mapbox_earcut` which is optimized for performance

### Performance Comparison

While Python is generally slower than C++, the implementation:
- Delegates heavy lifting to C libraries (XML parsing, PROJ, earcut)
- Uses efficient data structures and algorithms
- Avoids unnecessary data copying

For most use cases, the performance should be acceptable. If processing very large files, consider:
- Processing files in batches
- Using PyPy for improved Python execution speed
- Profiling to identify bottlenecks

## Differences from C++ Version

1. **Dependencies**:
   - C++: tinyxml2, PROJ, nlohmann_json, earcut.hpp
   - Python: pyproj, mapbox_earcut (built-in xml.etree.ElementTree and json)

2. **Memory Management**: Python handles memory automatically (no manual memory management)

3. **Namespace Handling**: Python implementation uses dictionary-based namespace mapping

4. **Error Handling**: Uses Python exceptions instead of exit() where appropriate

## Output Files

The program generates:
- **OBJ files**: `../obj/{tile_id}/{object_id}.obj`
- **GeoJSON**: `../test_geojson/{tile_id}.geojson`
- **JSON**: `../json/{tile_id}_sample.json` (if enabled)

## Coordinate Reference Systems

Default configuration:
- **Source CRS**: EPSG:6697 (JGD2011 Geographic 3D)
- **Target CRS**: EPSG:30169 (UTM Zone 54N)

These can be modified in `main.py`.

## Troubleshooting

### Module Import Errors
If you get import errors, make sure you're running from the `gml_io_py` directory:
```bash
cd gml_io_py
python main.py
```

### Coordinate Transformation Issues
If `pyproj` is not installed, the program will skip coordinate transformation and use original coordinates.

### Triangulation Issues
If `mapbox_earcut` is not available, the program will fall back to simple fan triangulation for convex polygons.

## License

This implementation follows the same license as the original C++ version.

## References

- CityGML 2.0: http://www.opengis.net/citygml/2.0
- PROJ: https://proj.org/
- pyproj: https://pyproj4.github.io/pyproj/
- mapbox-earcut: https://github.com/mapbox/earcut
