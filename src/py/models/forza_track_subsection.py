import struct
from mathutils import Vector
from models.index_type import IndexType
import utils.mesh_utils

class ForzaTrackSubSection:
    def __init__(self, f):
        
        assert(1 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        assert(2 == int.from_bytes(f.read(4), byteorder="big", signed=False))
        
        # name
        length_bytes = f.read(4)
        length = struct.unpack("<i", length_bytes)[0]
        name_bytes = f.read(length)
        self.name : str = name_bytes.decode("ascii").lower()

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
        self.uv_offset = Vector((struct.unpack(">f", f.read(4))[0],struct.unpack(">f", f.read(4))[0]))
        self.uv_tile = Vector((struct.unpack(">f", f.read(4))[0],struct.unpack(">f", f.read(4))[0]))

        # assert
        assert(3 == int.from_bytes(f.read(4), byteorder="big", signed=False))

        # indices
        f.read(4)
        self.indices = utils.mesh_utils.read_indices(f, int.from_bytes(f.read(4), byteorder="big", signed=False))

        num = int.from_bytes(f.read(4), byteorder="big", signed=False)
        if num != 0 and num != 1 and num != 2 and num != 5:
            raise RuntimeError("analyze this!")
        
        self.vertex_count = utils.mesh_utils.calculate_vertex_count(self.indices)
        self.face_count = utils.mesh_utils.calculate_face_count(self.indices, IndexType)
