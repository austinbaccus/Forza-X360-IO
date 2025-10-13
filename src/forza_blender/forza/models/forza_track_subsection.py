from forza_blender.forza.pvs.pvs_util import BinaryStream
from .index_type import IndexType

class IndexBuffer:
    def __init__(self, length: int, stride: int, data: bytes):
        self.is_32bit = stride == 4
        self.length = length
        self.stride = stride
        self.data = data

    def from_stream(stream: BinaryStream):
        version = stream.read_u32()
        if version >= 4:
            stream.skip(4)
        length = stream.read_u32()
        stride = stream.read_u32()
        data = stream.read(stride * length)
        return IndexBuffer(length, stride, data)

class ForzaTrackSubSection:
    def __init__(self, name: str, material_index: int, uv_offset: list[float], uv_scale: list[float], index_type: IndexType, index_buffer: IndexBuffer):
        self.name = name
        self.material_index = material_index
        self.uv_offset = uv_offset
        self.uv_scale = uv_scale
        self.index_type = index_type
        self.index_buffer = index_buffer

    def from_stream(stream: BinaryStream):
        assert(1 == stream.read_u32())
        assert(2 == stream.read_u32())
        
        # name
        name: str = stream.read_string("latin_1")

        stream.skip(4)

        # index type
        index_type: IndexType = IndexType(stream.read_u32())

        # skip and assert
        material_index = stream.read_u32()
        assert(1 == stream.read_u32())
        assert(0 == stream.read_u32())
        assert(0 == stream.read_u32())
        assert(0 == stream.read_u32())
        assert(0 == stream.read_u32())
        assert(1.0 == stream.read_f32())
        assert(1.0 == stream.read_f32())
        assert(1.0 == stream.read_f32())
        assert(1.0 == stream.read_f32())

        # uv
        uv_offset = [stream.read_f32() for _ in range(2)]
        uv_scale = [stream.read_f32() for _ in range(2)]

        index_buffer = IndexBuffer.from_stream(stream)

        stream.skip(4)
        return ForzaTrackSubSection(name, material_index, uv_offset, uv_scale, index_type, index_buffer)
