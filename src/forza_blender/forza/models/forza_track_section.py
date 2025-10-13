import struct
from typing import List
import numpy as np
from ..utils.mesh_util import generate_triangle_list
from .forza_track_subsection import ForzaTrackSubSection
from .forza_vertex import ForzaVertex
from .index_type import IndexType

class ForzaTrackSection:
    def __init__(self, f):
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
        self.size: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
        self.base_vertices = f.read(self.size * num)

        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # individual meshes
        sub_count = int.from_bytes(f.read(4), byteorder="big", signed=False)
        self.subsections :List[ForzaTrackSubSection] = [None] * sub_count

        for j in range(sub_count):
            self.subsections[j] = ForzaTrackSubSection(f)

    def generate_vertices(self):
        vertices = ForzaVertex(self.base_vertices, self.size)

        # uv adjustments
        sub = self.subsections[0] # assume that all submeshes have the same UV transform
        for texcoord in vertices.texcoords:
            if texcoord is None:
                continue
            texcoord *= sub.uv_tile
            texcoord += sub.uv_offset
            texcoord[:, 1] = 1.0 - texcoord[:, 1]

        faces = []
        for sub in self.subsections:
            indices = np.frombuffer(sub.indices, ">u4" if sub.index_is_32bit else ">u2")
            # convert tristrips to triangle list if needed
            if sub.index_type == IndexType.TriStrip:
                faces.append(generate_triangle_list(indices, 0xFFFFFF if sub.index_is_32bit else 0xFFFF))
            else:
                faces.append(indices.reshape(-1, 3))

        return vertices, np.concatenate(faces)
