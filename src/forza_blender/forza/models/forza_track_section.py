import struct
from typing import List
from ..utils.mesh_utils import generate_triangle_list, generate_triangle_list, generate_vertices
from .forza_track_subsection import ForzaTrackSubSection
from .forza_vertex import ForzaVertex
from .forza_vertex_type import ForzaVertexType
from .index_type import IndexType
from ..utils.forza_version import ForzaVersion

class ForzaTrackSection:
    def __init__(self, f, forza_version: ForzaVersion):
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        f.read(12)
        assert(0.0 == struct.unpack(">f", f.read(4))[0]  )
        f.read(12)
        assert(0.0 == struct.unpack(">f", f.read(4))[0])
        f.read(12)
        assert(0.0 == struct.unpack(">f", f.read(4))[0])
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # name
        length = int.from_bytes(f.read(4), byteorder="big", signed=False)
        name_bytes = f.read(length)
        self.name : str = name_bytes.decode("ascii")

        assert(2 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # forza vertex array
        num: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
        size: int = int.from_bytes(f.read(4), byteorder="big", signed=False)

        base_vertices: List[ForzaVertex] = [None] * num
        for i in range(num):
            base_vertices[i] = ForzaVertex(f, size, ForzaVertexType.Track, forza_version)

        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # subsections
        sub_count = int.from_bytes(f.read(4), byteorder="big", signed=False)
        self.subsections :List[ForzaTrackSubSection] = [None] * sub_count

        for j in range(sub_count):
            sub = ForzaTrackSubSection(f)

            # generate per-subsection vertices
            sub.vertices = generate_vertices(base_vertices, sub.indices)

            # uv adjustments
            for v in sub.vertices:
                v.texture0 *= sub.uv_tile
                v.texture1 *= sub.uv_tile
                v.texture0 += sub.uv_offset
                v.texture1 += sub.uv_offset
                v.texture0.y = 1.0 - v.texture0.y
                v.texture1.y = 1.0 - v.texture1.y

            # convert tristrips to triangle list if needed
            if sub.index_type == IndexType.TriStrip:
                sub.indices = generate_triangle_list(sub.indices, sub.face_count)

            self.subsections[j] = sub
