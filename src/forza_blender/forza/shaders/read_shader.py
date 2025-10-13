from forza_blender.forza.pvs.pvs_util import BinaryStream

class VertexElement: # _D3DVERTEXELEMENT9
    def __init__(self, type: int, usage: int, usage_index: int):
        self.type = type
        self.usage = usage
        self.usage_index = usage_index

    def from_stream(stream: BinaryStream):
        stream.skip(2 + 2)
        type = stream.read_u32()
        stream.skip(1)
        usage = stream.read_u8()
        usage_index = stream.read_u8()
        stream.skip(1)
        return VertexElement(type, usage, usage_index)

class VertexDeclaration: # D3D::CVertexDeclaration
    def __init__(self, elements: list[VertexElement]):
        self.elements = elements

    def from_stream(stream: BinaryStream):
        stream.skip(24)
        elements_length = stream.read_u32()
        stream.skip(4 + 16 + 4)
        elements = [VertexElement.from_stream(stream) for _ in range(elements_length)]
        return VertexDeclaration(elements)

class FXLShader: # CFXLShader
    def __init__(self, vdecl: VertexDeclaration):
        self.vdecl = vdecl

    def from_stream(stream: BinaryStream):
        type = stream.read_u32()
        if type != 0x101:
            raise RuntimeError("Wrong magic number.")
        stream.skip(4)
        shader_size = stream.read_u32()
        techniques_length = stream.read_u32()
        vdecls_length = stream.read_u32()
        if vdecls_length != 1:
            raise RuntimeError("new value")
        strides_length = stream.read_u32()
        if strides_length != 1:
            raise RuntimeError("new value")

        # m_data1
        stream.skip(4 + 4 * (techniques_length + vdecls_length * 2 + strides_length))

        # m_data2
        stream.skip(shader_size)

        # m_data3
        vdecl = VertexDeclaration.from_stream(stream) # TODO: loop vdecls_length
        return FXLShader(vdecl)
