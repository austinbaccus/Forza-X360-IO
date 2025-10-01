import struct
from typing import List
import forza.utils.mesh_utils
from forza.models.forza_track_subsection import ForzaTrackSubSection
from forza.models.forza_vertex import ForzaVertex
from forza.models.forza_vertex_type import ForzaVertexType
from forza.models.index_type import IndexType

class ForzaTrackSection:
    def __init__(self, f):
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

        base_vertices: List[ForzaVertex] = [None] * num
        for i in range(num):
            base_vertices[i] = ForzaVertex(f, size, ForzaVertexType.Track)

        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # subsections
        sub_count = self.Stream.read_uint32()
        self.subsections = [None] * sub_count

        for j in range(sub_count):
            sub = ForzaTrackSubSection(f)

            # generate per-subsection vertices
            sub.vertices = forza.utils.mesh_utils.generate_vertices(base_vertices, sub.indices)

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
                sub.indices = forza.utils.mesh_utils.generate_triangle_list(sub.indices, sub.face_count)

            self.subsections[j] = sub
