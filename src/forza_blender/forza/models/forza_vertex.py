import numpy as np
from mathutils import Vector # type: ignore

class ForzaVertex:
    def __init__(self, f, size: int):
        self.position = None
        self.texcoords = [None] * 3
        self.normal = None
        self.read_vertex(f, size)

    def read_vertex(self, f, size: int):
        if size == 12:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4")]))
            self.position = vertex["position"]
        elif size == 16:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "4V")]))
            self.position = vertex["position"]
        elif size == 20:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "4V"), ("texcoord0", ">2u2")]))
            self.position = vertex["position"]
            self.texcoords[0] = vertex["texcoord0"] / 65535
        elif size == 24:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "4V"), ("texcoord0", ">2u2"), ("texcoord1", ">2u2")]))
            self.position = vertex["position"]
            self.texcoords[0] = vertex["texcoord0"] / 65535
            self.texcoords[1] = vertex["texcoord1"] / 65535
        elif size == 28:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "4V"), ("texcoord0", ">2u2"), ("gap1", "8V")]))
            self.position = vertex["position"]
            self.texcoords[0] = vertex["texcoord0"] / 65535
        elif size == 32:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "4V"), ("texcoord0", ">2u2"), ("texcoord1", ">2u2"), ("gap1", "8V")]))
            self.position = vertex["position"]
            self.texcoords[0] = vertex["texcoord0"] / 65535
            self.texcoords[1] = vertex["texcoord1"] / 65535
        elif size == 36:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "8V"), ("texcoord0", ">2u2"), ("texcoord1", ">2u2"), ("gap1", "8V")]))
            self.position = vertex["position"]
            self.texcoords[0] = vertex["texcoord0"] / 65535
            self.texcoords[1] = vertex["texcoord1"] / 65535
        elif size == 40:
            vertex = np.frombuffer(f, np.dtype([("position", ">3f4"), ("gap0", "4V"), ("texcoord0", ">2u2"), ("texcoord1", ">2u2"), ("gap1", "16V")]))
            self.position = vertex["position"]
            self.texcoords[0] = vertex["texcoord0"] / 65535
            self.texcoords[1] = vertex["texcoord1"] / 65535
        else:
            raise RuntimeError("Vertex data is the wrong size.")

    def _get_normalized_101010(self, packed_value: int):
        # layout matches R10G10B10: bits [0..9]=X, [10..19]=Y, [20..29]=Z. Top 2 bits ignored.
        MASK10 = 0x3FF   # 10-bit mask (0b11_1111_1111)
        SIGN10 = 0x200   # bit 9 (sign bit in 10-bit two's complement)

        # wxtract raw 10-bit values
        ix = packed_value & MASK10
        iy = (packed_value >> 10) & MASK10
        iz = (packed_value >> 20) & MASK10

        # aign extend from 10 bits to Python int
        ix = ix | ~MASK10 if (ix & SIGN10) else ix
        iy = iy | ~MASK10 if (iy & SIGN10) else iy
        iz = iz | ~MASK10 if (iz & SIGN10) else iz

        # convert SNORM10 -> float in [-1,1]; special-case the most negative
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
