import struct
from .index_type import IndexType

class ForzaTrackSubSection:
    def __init__(self, f):
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(2 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        
        # name
        length = int.from_bytes(f.read(4), byteorder="big", signed=False)
        name_bytes = f.read(length)
        self.name : str = name_bytes.decode("latin_1")

        # lod
        self.lod : int = int.from_bytes(f.read(4), byteorder="big", signed=False)

        # index type
        self.index_type : IndexType = IndexType(int.from_bytes(f.read(4), byteorder="big", signed=False))

        # skip and assert
        f.read(4)
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(0 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(0 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(0 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(0 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(1.0 == struct.unpack(">f", f.read(4))[0])
        assert(1.0 == struct.unpack(">f", f.read(4))[0])
        assert(1.0 == struct.unpack(">f", f.read(4))[0])
        assert(1.0 == struct.unpack(">f", f.read(4))[0])

        # uv
        self.uv_offset = [struct.unpack(">f", f.read(4))[0],struct.unpack(">f", f.read(4))[0]]
        self.uv_tile = [struct.unpack(">f", f.read(4))[0],struct.unpack(">f", f.read(4))[0]]

        # assert
        assert(3 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # indices
        indicies_count = int.from_bytes(f.read(4), byteorder="big", signed=True) # 2
        indices_size = int.from_bytes(f.read(4), byteorder="big", signed=True) # 1
        self.index_is_32bit = indices_size == 4
        self.indices = f.read(indices_size * indicies_count)

        num = struct.unpack(">i", f.read(4))[0]
        if num != 0 and num != 1 and num != 2 and num != 5:
            raise RuntimeError("analyze this!")
