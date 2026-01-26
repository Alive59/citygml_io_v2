"""
GML Reader Module

This module provides functionality to read and parse CityGML 2.0 files.
Equivalent to gml_io.h in C++ implementation.
"""

import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple
import sys

from gml_mesh_component import MeshVertex


class GMLReader:
    """
    Reader for CityGML 2.0 files using XML parsing.

    This class parses CityGML files and extracts building geometry data
    including polygons, LOD (Level of Detail) information, and metadata.
    """

    def __init__(self, doc_path: str, lod_number: int = 2):
        """
        Initialize GML reader.

        Args:
            doc_path: Path to the GML/XML file
            lod_number: Level of Detail to extract (0-3)
        """
        try:
            self.tree = ET.parse(doc_path)
            self.root = self.tree.getroot()
        except ET.ParseError as e:
            print(f"Invalid path to XML/GML file: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"File not found: {doc_path}", file=sys.stderr)
            sys.exit(1)

        self.lod_num = lod_number

        # Data storage
        self.objects: List[List[str]] = []  # Coordinate strings per object
        self.object_ids: List[str] = []  # gml:id values
        self.object_type_ids: List[str] = []  # Object types (e.g., "bldg")
        self.object_member_lods: List[List[int]] = []  # LOD levels
        self.object_filters: List[List[bool]] = []  # Face filtering flags
        self.object_measured_height: List[float] = []  # Building heights
        self.gml_bounding: List[str] = []  # Bounding box

        # XML traversal stack
        self.nodes: List[ET.Element] = []

        # Namespace mappings
        self.ns = {
            'core': 'http://www.opengis.net/citygml/2.0',
            'gml': 'http://www.opengis.net/gml',
            'bldg': 'http://www.opengis.net/citygml/building/2.0',
            'uro': 'https://www.geospatial.jp/iur/uro/2.0'
        }

    def __del__(self):
        """Destructor."""
        print("Released GML.")

    def _get_tag_without_namespace(self, element: ET.Element) -> str:
        """Extract tag name without namespace."""
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    def _get_namespace_prefix(self, element: ET.Element) -> str:
        """Extract namespace prefix from element tag."""
        tag = element.tag
        if '}' in tag:
            ns_uri = tag.split('}')[0][1:]
            for prefix, uri in self.ns.items():
                if uri == ns_uri:
                    return prefix
        return ''

    def _read_gml_child_element(self, element: ET.Element, tag: str = '',
                                push: bool = True) -> Optional[ET.Element]:
        """
        Read a child element.

        Args:
            element: Parent element
            tag: Tag name to search for (empty string for first child)
            push: Whether to push element to navigation stack

        Returns:
            Child element or None
        """
        if tag:
            # Search for specific tag
            for child in element:
                if self._get_tag_without_namespace(child) == tag or child.tag.endswith(tag):
                    if push:
                        self.nodes.append(child)
                    return child
            return None
        else:
            # Return first child
            children = list(element)
            if children:
                if push:
                    self.nodes.append(children[0])
                return children[0]
            return None

    def _read_gml_sibling_element(self, element: ET.Element,
                                  tag: str = '') -> Optional[ET.Element]:
        """
        Read a sibling element.

        Args:
            element: Current element
            tag: Tag name to search for (empty string for next sibling)

        Returns:
            Sibling element or None
        """
        parent = None
        for node in self.nodes[:-1]:
            for child in node:
                if child == element:
                    parent = node
                    break
            if parent:
                break

        if not parent and len(self.nodes) > 0:
            # Try to find parent from root
            parent = self._find_parent(self.root, element)

        if not parent:
            return None

        siblings = list(parent)
        try:
            idx = siblings.index(element)
        except ValueError:
            return None

        if tag:
            # Search for specific sibling
            for i in range(idx + 1, len(siblings)):
                if (self._get_tag_without_namespace(siblings[i]) == tag or
                    siblings[i].tag.endswith(tag)):
                    if self.nodes and self.nodes[-1] == element:
                        self.nodes.pop()
                    self.nodes.append(siblings[i])
                    return siblings[i]
            return None
        else:
            # Return next sibling
            if idx + 1 < len(siblings):
                if self.nodes and self.nodes[-1] == element:
                    self.nodes.pop()
                self.nodes.append(siblings[idx + 1])
                return siblings[idx + 1]
            return None

    def _find_parent(self, root: ET.Element, element: ET.Element) -> Optional[ET.Element]:
        """Find parent of an element."""
        for child in root:
            if child == element:
                return root
            parent = self._find_parent(child, element)
            if parent is not None:
                return parent
        return None

    def _node_fall_back(self) -> Optional[ET.Element]:
        """Fall back to previous node in navigation stack."""
        if self.nodes:
            self.nodes.pop()
        if self.nodes:
            return self.nodes[-1]
        return None

    def gml_poslist_converter(self, pos_list: str) -> List[MeshVertex]:
        """
        Convert GML posList string to vertices.

        Args:
            pos_list: Space-separated coordinate string (x1 y1 z1 x2 y2 z2 ...)

        Returns:
            List of MeshVertex objects
        """
        vertices = []
        tokens = pos_list.strip().split()

        for i in range(0, len(tokens), 3):
            if i + 2 < len(tokens):
                try:
                    x = float(tokens[i])
                    y = float(tokens[i + 1])
                    z = float(tokens[i + 2])
                    vertices.append(MeshVertex(x, y, z))
                except ValueError:
                    continue

        return vertices

    def gml_object_reader(self, lod2_face_filter: str = ''):
        """
        Read building objects from GML file.

        Args:
            lod2_face_filter: Filter string for LOD2 faces (e.g., "bldg:WallSurface")
        """
        # Find root element
        root_elem = None
        for elem in self.root.iter():
            if 'CityModel' in elem.tag:
                root_elem = elem
                break

        if root_elem is None:
            print("Invalid XML/GML file: No root nodes.", file=sys.stderr)
            sys.exit(1)

        # Read bounding box
        bounded_by = None
        for child in root_elem:
            if 'boundedBy' in child.tag:
                bounded_by = child
                break

        if bounded_by is not None:
            for elem in bounded_by.iter():
                if 'lowerCorner' in elem.tag:
                    self.gml_bounding.append(elem.text or '')
                elif 'upperCorner' in elem.tag:
                    self.gml_bounding.append(elem.text or '')

        # Find all cityObjectMember elements
        city_object_members = []
        for child in root_elem:
            if 'cityObjectMember' in child.tag:
                city_object_members.append(child)

        print(f"Found {len(city_object_members)} cityObjectMember elements.")

        # Process each cityObjectMember
        for member in city_object_members:
            vertices_list = []
            object_lod = []
            object_filter = []

            # Get first child (should be Building or similar)
            building = list(member)[0] if list(member) else None
            if building is None:
                continue

            # Extract object type and ID
            tag = building.tag
            if '}' in tag:
                ns_uri = tag.split('}')[0][1:]
                local_name = tag.split('}')[1]
                ns_prefix = ''
                for prefix, uri in self.ns.items():
                    if uri == ns_uri:
                        ns_prefix = prefix
                        break
                self.object_type_ids.append(ns_prefix if ns_prefix else 'unknown')
            else:
                self.object_type_ids.append('unknown')

            # Get gml:id attribute
            gml_id = building.get('{http://www.opengis.net/gml}id') or building.get('id') or ''
            for attr_name, attr_value in building.attrib.items():
                if 'id' in attr_name.lower():
                    gml_id = attr_value
                    break
            self.object_ids.append(gml_id)

            # Extract measured height
            measured_height = -1.0
            is_measured_height_available = False
            for elem in building.iter():
                if 'measuredHeight' in elem.tag and elem.text:
                    try:
                        measured_height = float(elem.text)
                        if measured_height > 0.0:
                            is_measured_height_available = True
                        else:
                            measured_height = 5.0
                            is_measured_height_available = True
                    except ValueError:
                        pass
                    break

            if is_measured_height_available:
                self.object_measured_height.append(measured_height)
            else:
                self.object_measured_height.append(-1.0)

            # Extract geometry and posList elements
            string_filtered = False
            for elem in building.iter():
                tag_name = self._get_tag_without_namespace(elem)

                # Determine LOD number
                lod_num = -1
                if tag_name.startswith('lod'):
                    try:
                        lod_num = int(tag_name[3])
                    except (ValueError, IndexError):
                        lod_num = 3

                # Check for filter string
                if lod2_face_filter and elem.tag.endswith(lod2_face_filter):
                    string_filtered = True

                # Find posList elements
                if 'posList' in elem.tag:
                    pos_text = elem.text
                    if pos_text:
                        vertices_list.append(pos_text)
                        object_filter.append(string_filtered)

                        if lod_num != -1:
                            object_lod.append(lod_num)
                        else:
                            # Try to infer LOD from parent elements
                            parent = self._find_parent(building, elem)
                            while parent is not None and lod_num == -1:
                                parent_tag = self._get_tag_without_namespace(parent)
                                if parent_tag.startswith('lod'):
                                    try:
                                        lod_num = int(parent_tag[3])
                                    except (ValueError, IndexError):
                                        lod_num = 2
                                parent = self._find_parent(building, parent)

                            if lod_num == -1:
                                lod_num = self.lod_num

                            object_lod.append(lod_num)

                    string_filtered = False

            # Store object data
            if vertices_list:
                self.objects.append(vertices_list)
                self.object_member_lods.append(object_lod)
                self.object_filters.append(object_filter)
            else:
                # Remove the measured height if no geometry was found
                if is_measured_height_available or not is_measured_height_available:
                    self.object_measured_height.pop()

        print(f"Find {len(self.objects)} Elements.")

    def gml_polygon_converter(self, object_idx: int,
                             object_vertices: List[List[MeshVertex]],
                             series: bool = False):
        """
        Convert GML polygons to vertices.

        Args:
            object_idx: Index of the object
            object_vertices: Output list for vertices
            series: Whether to process as series (not implemented)
        """
        if not self.objects:
            raise ValueError("No objects loaded")

        if not series:
            for idx in range(len(self.objects[object_idx])):
                if self.object_member_lods[object_idx][idx] == self.lod_num:
                    vertices = self.gml_poslist_converter(self.objects[object_idx][idx])
                    object_vertices.append(vertices)
        else:
            print("Series mode not implemented.", file=sys.stderr)

    def object_filter_update(self, object_idx: int):
        """
        Update object filter to match LOD2 size.

        Args:
            object_idx: Index of the object
        """
        object_filter_updated = []
        for idx in range(len(self.object_filters[object_idx])):
            if self.get_object_component_lod(object_idx, idx) == 2:
                object_filter_updated.append(self.object_filters[object_idx][idx])

        self.object_filters[object_idx] = object_filter_updated

    # Getter methods
    def get_polygon(self, obj_idx: int, poly_idx: int) -> str:
        """Get polygon string at a certain index."""
        return self.objects[obj_idx][poly_idx]

    def get_object(self, obj_idx: int) -> List[str]:
        """Get whole object at a certain index."""
        return self.objects[obj_idx]

    def get_object_type(self, obj_idx: int) -> str:
        """Get object type at a certain index."""
        return self.object_type_ids[obj_idx]

    def get_object_id(self, obj_idx: int) -> str:
        """Get object ID at a certain index."""
        return self.object_ids[obj_idx]

    def get_object_member_lod(self, obj_idx: int) -> int:
        """Get maximum LOD in the object."""
        if self.object_member_lods[obj_idx]:
            return max(self.object_member_lods[obj_idx])
        return -1

    def check_object_member_lod(self, obj_idx: int, lod_num: int) -> bool:
        """Check if specified LOD exists in the object."""
        return lod_num in self.object_member_lods[obj_idx]

    def get_object_component_lod(self, obj_idx: int, cidx: int) -> int:
        """Get LOD of specific component in object."""
        return self.object_member_lods[obj_idx][cidx]

    def get_bounding(self) -> List[str]:
        """Get bounding corners of this file (lower, upper)."""
        return self.gml_bounding

    def get_object_num(self) -> int:
        """Get number of objects in GML file."""
        return len(self.objects)

    def get_object_mesh_num(self, obj_idx: int) -> int:
        """Get number of meshes in an object."""
        return len(self.objects[obj_idx])

    def get_object_measured_height(self, obj_idx: int) -> float:
        """Get height of current object."""
        return self.object_measured_height[obj_idx]

    def get_object_mesh_filtering(self, obj_idx: int, filter_idx: int) -> bool:
        """Get filtering status of current mesh."""
        return self.object_filters[obj_idx][filter_idx]
