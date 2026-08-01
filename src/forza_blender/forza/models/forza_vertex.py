import numpy as np
from forza_blender.forza.shaders.read_shader import VertexElement

class ForzaVertex:
    def __init__(self, position, normal, texcoords):
        self.position = position
        self.normal = normal
        self.texcoords = texcoords

    @staticmethod
    def from_buffer(buf: bytes, elements: list[VertexElement]):
        has_position = False
        has_normal = False
        has_texcoord = [False] * 3
        dtype_columns = []
        gap_index = 0
        for element in elements:
            if element.usage == 0: # POSITION0
                if element.usage_index == 0:
                    has_position = True
                    name = "position"
                else:
                    raise RuntimeError("Unexpected POSITION semantic number.")
                if element.type == 2761657: # D3DDECLTYPE_FLOAT3
                    format = ">3f4"
                else:
                    raise RuntimeError("Unexpected POSITION semantic type.")
            elif element.usage == 3:
                if element.usage_index == 0: # NORMAL0
                    has_normal = True
                    name = "normal"
                else:
                    raise RuntimeError("Unexpected NORMAL semantic number.")
                if element.type == 1712519: # D3DDECLTYPE_DEC4N
                    format = ">u4"
                else:
                    raise RuntimeError("Unexpected NORMAL semantic type.")
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
                    raise RuntimeError("Unexpected TEXCOORD semantic number.")
                if element.type == 2891865: # D3DDECLTYPE_USHORT2N
                    format = ">2u2"
                else:
                    raise RuntimeError("Unexpected TEXCOORD semantic type.")
            else:
                if element.type == 1712519 or element.type == 1583238: # D3DDECLTYPE_DEC4N, D3DDECLTYPE_D3DCOLOR
                    dtype_columns.append((F"gap{gap_index}", np.void, 4))
                    gap_index += 1
                else:
                    raise RuntimeError("Unknown semantic type.")
                continue
            dtype_columns.append((name, format))
        if not has_position:
            raise RuntimeError("No POSITION0 semantic.")
        vertex = np.frombuffer(buf, np.dtype(dtype_columns))
        normal = ForzaVertex._get_normalized_101010(vertex["normal"]) if has_normal else None
        texcoords = [vertex[F"texcoord{i}"] / 65535 if has_texcoord[i] else None for i in range(3)]
        return ForzaVertex(vertex["position"], normal, texcoords)

    # minimal guessing to read meshes without shaders
    @staticmethod
    def from_buffer_stride(buf: bytes, stride: int):
        vertex = np.frombuffer(buf, np.uint8).reshape(-1, stride)
        position = vertex[:, :12].view(">f4")
        normal = None
        texcoords = [None] * 3
        return ForzaVertex(position, normal, texcoords)

    # XMLoadDecN4()
    @staticmethod
    def _get_normalized_101010(packed_value):
        # layout matches R10G10B10: bits [0..9]=X, [10..19]=Y, [20..29]=Z. Top 2 bits ignored.
        MASK10 = 0x3FF   # 10-bit mask (0b11_1111_1111)
        SIGN10 = 22 # shift 10-bit sign bit to 32-bit sign bit (31 - 9 = 22)

        # extract raw 10-bit values
        i = (packed_value[:, None] >> np.array([0, 10, 20], np.uint32)) & MASK10

        # extend sign
        i = (i.view(np.int32) << SIGN10) >> SIGN10

        # convert SNORM10 -> float in [-1,1]
        i = i / 511

        return i
