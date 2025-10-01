import struct
from mathutils import Vector
from forza.models.forza_vertex_type import ForzaVertexType

class ForzaVertex:
    def __init__(self, f, size: int, vertex_type: ForzaVertexType):
        self.position: Vector = Vector((0.0,0.0,0.0))
        self.texture0: Vector = Vector((0.0,0.0))
        self.texture1: Vector = Vector((0.0,0.0))
        self.normal: Vector = Vector((0.0,0.0,0.0))
        self.read_vertex(f, size, vertex_type)

        # TODO convert to blender vertex and return it(?)

    def read_vertex(self, f, size: int, vertex_type: ForzaVertexType):
        if vertex_type == ForzaVertexType.Car: 
            return ForzaVertex._read_car_vertex()
        if vertex_type == ForzaVertexType.Track: 
            return ForzaVertex._read_track_vertex(f, size)

    def _read_track_vertex(self, f, size: int):
        if size == 12:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
        elif size == 16:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
        elif size == 20:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
            self.texture0 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
        elif size == 24:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
            self.texture0 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            self.texture1 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
        elif size == 28:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
            self.texture0 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            f.read(8)
        elif size == 32:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
            self.texture0 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            self.texture1 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            f.read(8)
        elif size == 36:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
            f.read(4)
            self.texture0 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            self.texture1 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            f.read(8)
        elif size == 40:
            x = struct.unpack(">f", f.read(4))[0]
            y = struct.unpack(">f", f.read(4))[0]
            z = struct.unpack(">f", f.read(4))[0]
            self.position = Vector((x, y, z))
            self.normal = ForzaVertex._get_normalized_101010(int.from_bytes(f.read(4), byteorder="big", signed=False))
            self.texture0 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            self.texture1 = Vector((self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False)), self._ushort_n(int.from_bytes(f.read(2), byteorder="big", signed=False))))
            f.read(16)
        else:
            raise RuntimeError("Vertex data is the wrong size.")

    def _read_car_vertex(self):
        raise RuntimeError("Reading car vertices is not supported.")
    
    def _get_normalized_101010(self, packed_value: int):
        # Layout matches R10G10B10: bits [0..9]=X, [10..19]=Y, [20..29]=Z. Top 2 bits ignored.
        MASK10 = 0x3FF   # 10-bit mask (0b11_1111_1111)
        SIGN10 = 0x200   # bit 9 (sign bit in 10-bit two's complement)

        # Extract raw 10-bit values
        ix = packed_value & MASK10
        iy = (packed_value >> 10) & MASK10
        iz = (packed_value >> 20) & MASK10

        # Sign extend from 10 bits to Python int
        ix = ix | ~MASK10 if (ix & SIGN10) else ix
        iy = iy | ~MASK10 if (iy & SIGN10) else iy
        iz = iz | ~MASK10 if (iz & SIGN10) else iz

        # Convert SNORM10 -> float in [-1,1]; special-case the most negative
        if ix == -512:
            ix = -1.0
        else:
            ix = ix / 511.0

        if iy == -512:
            iy = -1.0
        else:
            iy = iy / 511.0

        if iz == -512:
            iz = -1.0
        else:
            iz = iz / 511.0

        return Vector((ix,iy,iz))
    
    def _ushort_n(self, value: int) -> float:
        return (float(value) / 65535.0)