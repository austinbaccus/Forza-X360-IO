import struct
from typing import List
import forza.utils
from forza.models.forza_track_subsection import ForzaTrackSubSection
from forza.utils.forza_version import ForzaVersion
from forza.models.forza_vertex import ForzaVertex
from forza.models.forza_vertex_type import ForzaVertexType
from forza.models.index_type import IndexType

class ForzaTrackSection:
    def __init__(self, f, forza_version: ForzaVersion):
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        f.read(4)
        assert(0.0 == struct.unpack(">f", f.read(4))[0])
        f.read(4)
        assert(0.0 == struct.unpack(">f", f.read(4))[0])
        f.read(4)
        assert(0.0 == struct.unpack(">f", f.read(4))[0])
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # name
        length = struct.unpack("<i", f.read(4))[0]
        name_bytes = f.read(length)
        self.name : str = name_bytes.decode("ascii").lower()
        parts = self.name.split('_')
        self.type = parts[0].lower()
        self.name = self.name[self.name.index('_') + 1:]

        assert(2 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # forza vertex array
        num: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
        size: int = int.from_bytes(f.read(4), byteorder="big", signed=False)

        base_vertices: List[ForzaVertex] = [None] * num  # type: ignore
        for i in range(num):
            base_vertices[i] = ForzaVertex(f, size, ForzaVertexType.Track)

        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        # BoundingBox.from_vertices(base_vertices) this does nothing?

        # Subsections
        sub_count = self.Stream.read_uint32()
        self.subsections = [None] * sub_count  # type: ignore

        for j in range(sub_count):
            sub = ForzaTrackSubSection(f)

            # Generate per-subsection vertices (and possibly remapped indices)
            # If your Utilities.generate_vertices only returns vertices, drop the second assignment.
            verts, indices = forza.utils.mesh_utils.generate_vertices(base_vertices, sub.Indices)
            sub.Vertices = verts
            sub.Indices = indices

            # UV adjustments
            for v in sub.Vertices:
                v.texture0 *= sub.UVtile
                v.texture1 *= sub.UVtile
                v.texture0 += sub.UVoffset
                v.texture1 += sub.UVoffset
                v.texture0.y = 1.0 - v.texture0.y
                v.texture1.y = 1.0 - v.texture1.y

            # Convert tristrips to triangle list if needed
            if sub.IndexType == IndexType.TriStrip:
                sub.Indices = forza.utils.mesh_utils.generate_triangle_list(sub.Indices, sub.FaceCount)

            self.subsections[j] = sub
