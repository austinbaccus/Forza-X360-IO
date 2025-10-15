import bpy # type: ignore
import numpy as np

from forza_blender.forza.pvs.pvs_util import BinaryStream

# CAFF
class HeaderUnknown1:
    def __init__(self, a_length, b_length, b_offsets_length):
        self.a_length = a_length
        self.b_length = b_length
        self.b_offsets_length = b_offsets_length

    def from_stream(stream: BinaryStream):
        a_length = stream.read_u32()
        stream.skip(4)
        b_length = stream.read_u32()
        b_offsets_length = stream.read_u32()
        return HeaderUnknown1(a_length, b_length, b_offsets_length)

class AllocationBlockInfo:
    def __init__(self, name, uncompressed_size):
        self.index = -1
        self.address = -1
        self.name = name
        self.uncompressed_size = uncompressed_size

    def from_stream(stream: BinaryStream):
        name = stream.read_cstring(11)
        stream.skip(5)
        uncompressed_size = stream.read_u32()
        stream.skip(20)
        return AllocationBlockInfo(name, uncompressed_size)

class Header:
    def __init__(self, assets_length, sections_length, unk_1, unk_2, data_allocation_blocks_size, header_size, allocation_blocks):
        self.assets_length = assets_length
        self.sections_length = sections_length
        self.unk_1 = unk_1
        self.unk_2 = unk_2
        self.data_allocation_blocks_size = data_allocation_blocks_size
        self.header_size = header_size
        self.allocation_blocks = allocation_blocks

    def from_stream(stream: BinaryStream):
        stream.skip(24)
        assets_length = stream.read_u32()
        sections_length = stream.read_u32()
        unk_1 = HeaderUnknown1.from_stream(stream)
        unk_2 = HeaderUnknown1.from_stream(stream)
        stream.skip(4)
        data_allocation_blocks_size = stream.read_u32()
        header_size = stream.read_u32()
        stream.skip(1)
        allocation_blocks_length = stream.read_u8()
        stream.skip(2)
        allocation_blocks = [AllocationBlockInfo.from_stream(stream) for _ in range(allocation_blocks_length)]
        return Header(assets_length, sections_length, unk_1, unk_2, data_allocation_blocks_size, header_size, allocation_blocks)

class SectionInfo:
    def deserialize(self, stream: BinaryStream):
        stream.skip(4)
        self.asset_offset = stream.read_u32()
        self.asset_size = stream.read_u32()
        self.allocation_block_index = stream.read_u8()
        stream.skip(1)

class TableUnknownBHeader:
    def deserialize(self, stream: BinaryStream):
        self.source_section_index = stream.read_u32()
        self.destination_section_index = stream.read_u32()
        self.offsets_length = stream.read_u32()

class TableUnknownB:
    def deserialize(self, stream: BinaryStream, unk: HeaderUnknown1):
        self.headers = [TableUnknownBHeader() for _ in range(unk.b_length)]
        for header in self.headers:
            header.deserialize(stream)
        self.offsets = [None] * unk.b_offsets_length
        for i in range(unk.b_offsets_length):
            self.offsets[i] = stream.read_u32()

    def apply(self, stream: BinaryStream, allocation_blocks: list[AllocationBlockInfo], sections: list[SectionInfo]):
        i = 0
        for header in self.headers:
            src_section = sections[header.source_section_index - 1]
            dst_section = sections[header.destination_section_index - 1]
            src_base = allocation_blocks[src_section.allocation_block_index - 1].address + src_section.asset_offset
            dst_base = allocation_blocks[dst_section.allocation_block_index - 1].address + dst_section.asset_offset
            for _ in range(header.offsets_length):
                with stream.scoped_seek(src_base + self.offsets[i]):
                    with stream.scoped_seek(0, os.SEEK_CUR):
                        dst_offset = stream.read_u32()
                    stream.write_u32(dst_base + dst_offset)
                i += 1

class Rendergraph:
    def deserialize(self, stream: BinaryStream):
        type_and_version = stream.read(28)
        if type_and_version != b"\x72\x65\x6E\x64\x65\x72\x67\x72\x61\x70\x68\x00\x33\x30\x2E\x30\x36\x2E\x30\x36\x2E\x30\x30\x33\x36\x00\x00\x00":
            raise RuntimeError("Wrong asset type or version.")
        stream.skip(224)
        shaders_data_address = stream.read_u32()

        stream.seek(shaders_data_address + 12 * 3)
        # vertex buffers
        buffers_address = stream.read_u32()
        stream.skip(4)
        buffers_length = stream.read_u32()
        self.vertex_buffers = [None] * buffers_length
        with stream.scoped_seek(buffers_address):
            for i in range(buffers_length):
                stream.skip(4)
                buffer_address = stream.read_u32()
                buffer_size = stream.read_u32()
                with stream.scoped_seek(buffer_address):
                    self.vertex_buffers[i] = stream.read(buffer_size)
        # index buffers
        buffers_address = stream.read_u32()
        buffers_length = stream.read_u32()
        self.index_buffers = [None] * buffers_length
        with stream.scoped_seek(buffers_address):
            for i in range(buffers_length):
                stream.skip(4)
                buffer_address = stream.read_u32()
                buffer_size = stream.read_u32()
                buffer_format = stream.read_u32()
                if buffer_format != 1: # D3DFMT_INDEX16
                    raise RuntimeError("Index buffer format is not D3DFMT_INDEX16.")
                with stream.scoped_seek(buffer_address):
                    self.index_buffers[i] = stream.read(buffer_size)
    
    def process_mesh(self, name):
        # add dummy materials to each index buffer
        meshes = [[] for _ in range(len(self.vertex_buffers) + 15)]
        vertexes_lengths = [0] * (len(self.vertex_buffers) + 15)
        vertexes_positions = [None] * (len(self.vertex_buffers) + 15)

        # TODO: flip loop to vertex_buffers len
        j = -1
        for i in range(len(self.index_buffers)):
            mesh_indexes = np.frombuffer(self.index_buffers[i], np.dtype(">u2")) # np.uint16
            # mesh_indexes_diff = np.diff(np.sort(mesh_indexes))

            if mesh_indexes[0] == 0:
            # if mesh_indexes[0] == 0 and (j < 0 or len(self.vertex_buffers[j]) % vertexes_lengths[j] == 0):
            # if mesh_indexes.min() == 0:
            # if mesh_indexes.min() == 0 and ((mesh_indexes_diff >= 0) & (mesh_indexes_diff <= 1)).all():
                j += 1
            vertexes_length = mesh_indexes.max() + 1
            # if vertexes_length < vertexes_lengths[j]:
            #     raise RuntimeError()
            if vertexes_length > vertexes_lengths[j]:
                vertexes_lengths[j] = vertexes_length
            meshes[j].append(mesh_indexes)

        for i in range(len(self.vertex_buffers)):
            vertex_buffer = self.vertex_buffers[i]
            if len(vertex_buffer) % vertexes_lengths[i] != 0:
                raise RuntimeError()
            stride = len(vertex_buffer) // vertexes_lengths[i]
            
            # replace with structured array? np.dtype("(3)>f4, (8)B"); 8 = 20(stride) - 12(position attribute size)
            arr = np.frombuffer(vertex_buffer, np.uint8).reshape(-1, stride)
            vertexes_positions[i] = arr[:, :12].view(np.dtype(">f4")) # np.float32

        for i in range(len(self.vertex_buffers)):
            mesh_indexes = np.concatenate(meshes[i]).reshape(-1, 3)
            mesh_vertexes_positions = vertexes_positions[i]
            # mesh_vertexes_positions = mesh_vertexes_positions @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
            mesh_vertexes_positions = mesh_vertexes_positions @ np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]])
            mesh = bpy.data.meshes.new(name=name)
            mesh.from_pydata(mesh_vertexes_positions, [], mesh_indexes, False)
            mesh.validate()
            obj = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(obj)
            # TODO: assign materials

    # def process_mesh(self):
    #     meshes_indexes = [None] * len(self.index_buffers)
    #     vertexes_lengths = [None] * len(self.vertex_buffers)
    #     meshes = [None] * len(self.index_buffers)
    #     vertexes_positions = [None] * len(self.index_buffers)

    #     j = 0
    #     for i in range(len(self.index_buffers)):
    #         index_buffer = self.index_buffers[i]
    #         meshes_indexes[i] = np.frombuffer(index_buffer, np.dtype(">u2")) # np.uint16

    #         vertexes_length = meshes_indexes[i].max() - meshes_indexes[i].min() + 1
    #         if meshes_indexes[i].min() == 0:
    #             vertex_buffer = self.vertex_buffers[j]
    #             vertexes_lengths[j] = vertexes_length
    #             j += 1
    #         else:
    #             # TODO: replace with continuity check
    #             if meshes_indexes[i].min() != vertexes_lengths[j - 1]:
    #                 raise RuntimeError()
    #             vertexes_lengths[j - 1] += vertexes_length
    #         meshes[i] = j - 1

    #     for i in range(len(self.vertex_buffers)):
    #         vertex_buffer = self.vertex_buffers[i]
    #         if len(vertex_buffer) % vertexes_lengths[i] != 0:
    #             raise RuntimeError()
    #         stride = len(vertex_buffer) // vertexes_lengths[i]
            
    #         # replace with structured array? np.dtype("(3)>f4, (8)B")
    #         arr = np.frombuffer(vertex_buffer, np.uint8).reshape(-1, stride)
    #         vertexes_positions[i] = arr[:, :12].view(np.dtype(">f4")) # np.float32

    #     for i in range(len(self.index_buffers)):
    #         mesh_vertexes_positions = vertexes_positions[meshes[i]][meshes_indexes[i].min():meshes_indexes[i].max() + 1]
    #         mesh = bpy.data.meshes.new(name="Mesh")
    #         mesh.from_pydata(mesh_vertexes_positions, [], (meshes_indexes[i] - meshes_indexes[i].min()).reshape(-1, 3), False)
    #         mesh.validate()
    #         obj = bpy.data.objects.new("Mesh", mesh)
    #         bpy.context.collection.objects.link(obj)

class CAFF:
    def __init__(self, asset):
        self.asset = asset

    def from_stream(stream: BinaryStream):
        header = Header.from_stream(stream)
        
        address = header.header_size
        for i, allocation_block in enumerate(header.allocation_blocks):
            allocation_block.index = i
            allocation_block.address = address
            address += allocation_block.uncompressed_size
        
        data_allocation_block = next(allocation_block for allocation_block in header.allocation_blocks if allocation_block.name == ".data")
        # data_allocation_block_index = next(i for i in range(len(header.allocation_blocks)) if header.allocation_blocks[i].name == ".data")
        # data_allocation_block = header.allocation_blocks[data_allocation_block_index]

        # table 0
        stream.seek(data_allocation_block.address + header.data_allocation_blocks_size)
        assets_names_size = stream.read_u32()
        stream.skip(4 * header.assets_length + assets_names_size)
        unk_names_size = stream.read_u32()
        stream.skip(unk_names_size)
        sections_info = [SectionInfo() for _ in range(header.sections_length)]
        for section_info in sections_info:
            section_info.deserialize(stream)

        # table 1
        if header.unk_1.a_length > 0 or header.unk_2.a_length > 0:
            raise RuntimeError("new variable")
        
        unk_1_b = TableUnknownB()
        unk_1_b.deserialize(stream, header.unk_1)
        unk_2_b = TableUnknownB()
        unk_2_b.deserialize(stream, header.unk_2)

        # fixup
        unk_1_b.apply(stream, header.allocation_blocks, sections_info)
        unk_2_b.apply(stream, header.allocation_blocks, sections_info)

        #
        # TODO: find place where it walks through. how does it ignores pool?
        for section_info in sections_info:
            if section_info.allocation_block_index != data_allocation_block.index:
                continue
            # TODO: replace by list of assets? rendergraph is just one of asset types?
            #   add texture asset support
            asset = Rendergraph()
            with stream.scoped_seek(data_allocation_block.address + section_info.asset_offset):
                asset.deserialize(stream)
            # assumption that the model is in the 1st asset
            break

        return CAFF(asset)

# # 1 model
# input_path = R"E:\downloads\FM2\Media\tracks\testtrackinfield\bin\testtrackinfieldout.00217.rmb.bin"
# # input_path = R"E:\downloads\FM2\Media\tracks\testtrackinfield\bin\testtrackinfieldout.sky.rmb.bin"
# # input_path = R"E:\downloads\FM2\Media\tracks\testtrackinfield\bin\testtrackinfieldout.00048.rmb.bin"
# # input_path = R"E:\downloads\FM2\Media\tracks\newyork\bin\newyorkout.00133.rmb.bin"
# # input_path = R"E:\downloads\FM2\Media\tracks\Sebring\bin\sebringout.01206.rmb.bin" # not fixed bug

# stream = BinaryStream.from_path(input_path, ">")

# model = CAFF.from_stream(stream)
# model.asset.process_mesh("Mesh")


for directory, _, filenames in os.walk(src_path):
    for filename in filenames:
        path = os.path.join(directory, filename)
        print(path)
        stream = BinaryStream.from_path(path, ">")
        model = CAFF.from_stream(stream)
        model.asset.process_mesh(filename[:-8] + "_a")
