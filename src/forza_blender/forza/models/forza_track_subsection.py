from forza_blender.forza.pvs.pvs_util import BinaryStream
from .index_type import IndexType

class ForzaTrackSubSection:
    def __init__(self, stream: BinaryStream):
        assert(1 == stream.read_u32())
        assert(2 == stream.read_u32())
        
        # name
        self.name: str = stream.read_string("latin_1")

        stream.skip(4)

        # index type
        self.index_type: IndexType = IndexType(stream.read_u32())

        # skip and assert
        stream.skip(4)
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
        self.uv_offset = [stream.read_f32() for _ in range(2)]
        self.uv_tile = [stream.read_f32() for _ in range(2)]

        # assert
        assert(3 == stream.read_u32())

        # indices
        indicies_count = stream.read_s32() # 2
        indices_size = stream.read_s32() # 1
        self.index_is_32bit = indices_size == 4
        self.indices = stream.read(indices_size * indicies_count)

        stream.skip(4)
