import numpy as np
from forza_blender.forza.pvs.pvs_util import BinaryStream
from forza_blender.forza.shaders.read_shader import VertexElement
from ..utils.mesh_util import generate_triangle_list
from .forza_track_subsection import ForzaTrackSubSection
from .forza_vertex import ForzaVertex
from .index_type import IndexType

class VertexBuffer:
    def __init__(self, length: int, stride: int, data: bytes):
        self.length = length
        self.stride = stride
        self.data = data

    def from_stream(stream: BinaryStream):
        assert(2 == stream.read_u32())
        length: int = stream.read_u32()
        stride: int = stream.read_u32()
        data = stream.read(stride * length)
        return VertexBuffer(length, stride, data)

class ForzaTrackSection:
    def __init__(self, name: str, vertex_buffer: VertexBuffer, subsections: list[ForzaTrackSubSection]):
        self.name = name
        self.vertex_buffer = vertex_buffer
        self.subsections = subsections

    def from_stream(stream: BinaryStream):
        assert(1 == stream.read_u32())
        stream.skip(12)
        assert(0.0 == stream.read_f32())
        stream.skip(12)
        assert(0.0 == stream.read_f32())
        stream.skip(12)
        assert(0.0 == stream.read_f32())
        assert(1 == stream.read_u32())

        # name
        name: str = stream.read_string("latin_1")

        vertex_buffer = VertexBuffer.from_stream(stream)

        assert(1 == stream.read_u32())

        # individual meshes
        sub_count = stream.read_u32()
        subsections = [ForzaTrackSubSection.from_stream(stream) for _ in range(sub_count)]

        return ForzaTrackSection(name, vertex_buffer, subsections)
        

    def generate_vertices(self, elements: list[VertexElement]):
        vertices: ForzaVertex = ForzaVertex.from_buffer(self.vertex_buffer.data, elements)

        # uv adjustments
        sub = self.subsections[0] # assume that all submeshes have the same UV transform
        for texcoord in vertices.texcoords:
            if texcoord is None:
                continue
            texcoord *= sub.uv_scale
            texcoord += sub.uv_offset
            texcoord[:, 1] = 1.0 - texcoord[:, 1]

        faces = []
        for sub in self.subsections:
            indices = np.frombuffer(sub.index_buffer.data, ">u4" if sub.index_buffer.is_32bit else ">u2")
            # convert tristrips to triangle list if needed
            if sub.index_type == IndexType.TriStrip:
                faces.append(generate_triangle_list(indices, 0xFFFFFF if sub.index_buffer.is_32bit else 0xFFFF))
            else:
                faces.append(indices.reshape(-1, 3))

        return vertices, np.concatenate(faces)
