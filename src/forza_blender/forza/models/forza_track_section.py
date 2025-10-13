import struct
from typing import List
from ..utils.mesh_util import generate_triangle_list
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
        self.name : str = name_bytes.decode("latin_1")

        assert(2 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # forza vertex array
        num: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
        size: int = int.from_bytes(f.read(4), byteorder="big", signed=False)

        self.base_vertices: List[ForzaVertex] = [None] * num
        for i in range(num):
            self.base_vertices[i] = ForzaVertex(f, size, ForzaVertexType.Track, forza_version)

        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # individual meshes
        sub_count = int.from_bytes(f.read(4), byteorder="big", signed=False)
        self.subsections :List[ForzaTrackSubSection] = [None] * sub_count

        for j in range(sub_count):
            self.subsections[j] = ForzaTrackSubSection(f)

    def generate_vertices(self):
        vertices = self.base_vertices

        # uv adjustments
        sub = self.subsections[0] # assume that all submeshes have the same UV transform
        for v in vertices:
            v.texture0 *= sub.uv_tile
            v.texture1 *= sub.uv_tile
            v.texture0 += sub.uv_offset
            v.texture1 += sub.uv_offset
            v.texture0.y = 1.0 - v.texture0.y
            v.texture1.y = 1.0 - v.texture1.y

        indices = []
        for sub in self.subsections:
            # convert tristrips to triangle list if needed
            if sub.index_type == IndexType.TriStrip:
                indices.extend(generate_triangle_list(sub.indices, sub.face_count))
            else:
                indices.extend(sub.indices)

        return vertices, indices
