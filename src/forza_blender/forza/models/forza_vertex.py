import numpy as np
from forza_blender.forza.shaders.read_shader import VertexElement
from mathutils import Vector # type: ignore

class ForzaVertex:
    def __init__(self, position, texcoords):
        self.position = position
        self.texcoords = texcoords
        self.normal = None

    def from_buffer(buf: bytes, elements: list[VertexElement]):
        has_position = False
        has_texcoord = [False] * 3
        dtype_columns = []
        gap_index = 0
        for element in elements:
            if element.usage == 0: # POSITION0
                if element.usage_index == 0:
                    has_position = True
                    name = "position"
                else:
                    raise RuntimeError()
                if element.type == 2761657: # D3DDECLTYPE_FLOAT3
                    format = ">3f4"
                else:
                    raise RuntimeError()
            elif element.usage == 5:
                if element.usage_index == 0: # TEXCOORD0
                    has_texcoord[0] = True
                    name = "texcoord0"
                elif element.usage_index == 1: # TEXCOORD1
                    has_texcoord[1] = True
                    name = "texcoord1"
                elif element.usage_index == 2: # TEXCOORD2
                    has_texcoord[2] = True
                    name = "texcoord2"
                else:
                    raise RuntimeError()
                if element.type == 2891865: # D3DDECLTYPE_USHORT2N
                    format = ">2u2"
                else:
                    raise RuntimeError()
            else:
                if element.type == 1712519 or element.type == 1583238: # D3DDECLTYPE_DEC4N, D3DDECLTYPE_D3DCOLOR
                    dtype_columns.append((F"gap{gap_index}", np.void, 4))
                    gap_index += 1
                else:
                    raise RuntimeError()
                continue
            dtype_columns.append((name, format))
        if not has_position:
            raise RuntimeError()
        vertex = np.frombuffer(buf, np.dtype(dtype_columns))
        texcoords = [vertex[F"texcoord{i}"] / 65535 if has_texcoord[i] else None for i in range(3)]
        return ForzaVertex(vertex["position"], texcoords)

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
