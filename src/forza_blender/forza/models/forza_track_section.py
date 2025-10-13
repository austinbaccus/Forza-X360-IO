from typing import List
import numpy as np
from forza_blender.forza.pvs.pvs_util import BinaryStream
from ..utils.mesh_util import generate_triangle_list
from .forza_track_subsection import ForzaTrackSubSection
from .forza_vertex import ForzaVertex
from .index_type import IndexType

class ForzaTrackSection:
    def __init__(self, stream: BinaryStream):
        assert(1 == stream.read_u32())
        stream.skip(12)
        assert(0.0 == stream.read_f32())
        stream.skip(12)
        assert(0.0 == stream.read_f32())
        stream.skip(12)
        assert(0.0 == stream.read_f32())
        assert(1 == stream.read_u32())

        # name
        self.name: str = stream.read_string("latin_1")

        assert(2 == stream.read_u32())

        # forza vertex array
        num: int = stream.read_u32()
        self.size: int = stream.read_u32()
        self.base_vertices = stream.read(self.size * num)

        assert(1 == stream.read_u32())

        # individual meshes
        sub_count = stream.read_u32()
        self.subsections: List[ForzaTrackSubSection] = [ForzaTrackSubSection(stream) for _ in range(sub_count)]
        

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
