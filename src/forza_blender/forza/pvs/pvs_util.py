from collections import defaultdict
from collections.abc import ByteString
import contextlib
# from dataclasses import dataclass
import io
import os
import struct

# IOSys module; iosys:Unity_IOSys_000.obj
class BinaryStream:
    # TODO: replace Reader with read_struct(self, st: struct.Struct)
    class Reader:
        def __init__(self, stream: io.BytesIO, fmt: str): # BinaryIO
            self._stream = stream
            # TODO: check native vs little-endian performance (empty, @, =, <)
            self.struct = struct.Struct(fmt)
            self.size = self.struct.size

        def read(self):
            buf = self._stream.read(self.size) # TODO: compare self.size with self.struct.size
            # if not buf: # TODO: try remove this check
            #     return None
            return self.struct.unpack(buf)[0]

        def write(self, value):
            buf = self.struct.pack(value)
            self._stream.write(buf)

    def __init__(self, stream: io.BytesIO, endianness: str):
        self._stream = stream

        self._u8 = self.Reader(self._stream, endianness + "B")
        self._s16 = self.Reader(self._stream, endianness + "h")
        self._u16 = self.Reader(self._stream, endianness + "H")
        self._s32 = self.Reader(self._stream, endianness + "i")
        self._u32 = self.Reader(self._stream, endianness + "I")
        self._f16 = self.Reader(self._stream, endianness + "e")
        self._f32 = self.Reader(self._stream, endianness + "f")
    
    # TODO: move to ContentManager
    #   s: BinaryStream = cm.open_file(path)
    @staticmethod
    def from_path(path: str, endianness: str = ""):
        with open(path, "rb", 0) as f:
            return BinaryStream.from_buffer(memoryview(f.read()), endianness)
    
    @staticmethod
    def from_buffer(buffer: memoryview, endianness: str = ""):
        return BinaryStream(io.BytesIO(buffer), endianness)
    
    # @contextlib.contextmanager
    # def scope(self):
    #     p = self.tell()
    #     yield
    #     self.seek(p)
    
    @contextlib.contextmanager
    def scoped_seek(self, offset: int, whence: int = os.SEEK_SET):
        p = self.tell()
        self.seek(offset, whence)
        yield
        self.seek(p)

    def getbuffer(self):
        return self._stream.getbuffer()

    # non-stream behavior. replace with yield, seek and read buffers
    # but read may copy instead of pass memoryview
    # def __getitem__(self, key: slice):
    #     return self.getbuffer()[key] # replace with self.__buffer[key] ?
    
    def tell(self): # uint32_t GetPosition()
        return self._stream.tell()
    
    def seek(self, offset: int, whence: int = os.SEEK_SET): # bool Seek(int32_t offsetBytes, IOSys::EFileSeekOrigin origin)
        return self._stream.seek(offset, whence)
    
    def skip(self, offset: int):
        return self._stream.seek(offset, os.SEEK_CUR)
    
    def size(self): # uint64_t AvailableToRead()
        with self.scoped_seek(0, io.SEEK_END):
            return self.tell()

    def seekable(self):
        return self._stream.seekable()

    def read(self, size: int | None = None):
        # TODO: compare perf with getbuffer()[tell():tell()+size]
        return self._stream.read(size)
    
    # TODO: compare bytes vs memoryview for small data
    # maybe no need to split read and read_big
    def read_big(self, size: int):
        return self.getbuffer()[self.tell():self.tell() + size]

    def read_list(self, _VT): # IOSys::CBinaryStream::SerializeContainer<std::vector<T>> and std::list<T>
        length = self.read_u32() # IOSys::CBinaryStream::Serialize<unsigned long>("count")
        return [_VT() for _ in range(length)]
        # IOSys::CBinaryStream::Serialize<std::vector<ISerializable *>>
        # std_vector = [_VT() for _ in range(length)]
        # for it in std_vector:
        #     it.deserialize(self._stream)
        # return std_vector

    def read_string(self, encoding: str = "ascii"): # IOSys::CBinaryStream::Serialize<std::string>
        length = self.read_u32()
        return self._stream.read(length).decode(encoding)

    def read_7bit_string(self, encoding: str = "ascii"):
        length = self.read_7bit()
        return self._stream.read(length).decode(encoding)

    # null-terminated string
    def read_cstring(self, size: int, encoding: str = "ascii"):
        buf = self.read(size)
        return buf.split(b"\x00", 1)[0].decode(encoding)

    def read_cstrings(self, size: int, encoding: str = "ascii"):
        buf = self._stream.read(size)
        l = buf.split(b"\x00")
        return [b.decode(encoding) for b in l]

    def read_cstring_variable(self, encoding: str = "ascii"):
        buf = self._stream.getbuffer()
        s_begin = self._stream.tell()
        s_end = s_begin
        while buf[s_end] != 0:
            s_end += 1
        result = self._stream.read(s_end - s_begin).decode(encoding)
        self._stream.seek(1, os.SEEK_CUR)
        return result

    def read_u8(self) -> int:
        return self._u8.read()
    
    def read_s16(self) -> int:
        return self._s16.read()
    
    def read_u16(self) -> int:
        return self._u16.read()
    
    def read_s32(self) -> int:
        return self._s32.read() # TODO: compare struct.unpack with int.from_bytes
    
    def read_u32(self) -> int:
        return self._u32.read()
    
    def read_f16(self) -> float:
        return self._f16.read()
    
    def read_f32(self) -> float:
        return self._f32.read()
    
    # TODO: remove when replaced by numpy, since these types used only in large buffers
    def read_sn16(self):
        return self.read_s16() / 32767
    
    def read_un8(self):
        return self.read_u8() / 255
    
    def read_un16(self):
        return self.read_u16() / 65535
    
    def read_7bit(self):
        value = 0
        shift = 0
        while True:
            value_byte = self.read_u8()
            value |= (value_byte & 0x7F) << shift
            shift += 7
            if value_byte & 0x80 == 0:
                break
        return value

    def write(self, buf: bytes):
        return self._stream.write(buf)
    
    def write_u8(self, value: int):
        return self._u8.write(value)
    
    def write_s16(self, value: int):
        return self._s16.write(value)
    
    def write_u16(self, value: int):
        return self._u16.write(value)
    
    def write_s32(self, value: int):
        return self._s32.write(value)
    
    def write_u32(self, value: int):
        return self._u32.write(value)
    
    def write_f32(self, value: float):
        return self._f32.write(value)
    
    def write_padding(self, alignment: int):
        pos = self.tell()
        padding = -pos % alignment
        self.write(b"\x00" * padding)

    # Deserialize<std::vector<std::string>>()
    # Deserialize<std::vector<T>>(T &obj) # T is ISerializable
    #   obj.Deserialize()

    # TODO: split into 2 classes: Serializer, Deserializer inherited from SerializableStream
    #   Serializer # def serialize_u32(value: int) -> int: return int.from_bytes(stream.read(4))
    #   Deserializer # def serialize_u32(value: int) -> int: stream.write(value.to_bytes()), return value
    # FileStream, MemoryStream inherit BinaryStream
    # SerializableStream contains BinaryStream field which may be FileStream or MemoryStream

# BundleFile module; bundlefile:Unity_BundleFile_000.obj
class Tag: # enum CommonModel::Serialization::Tags::Enum
    # bundle
    Grub = 0x47727562 # 'Grub'; BundleTag

    # metadata
    Id = 0x49642020 # 'Id  '
    Name = 0x4E616D65 # 'Name'

    TXCH = 0x54584348 # 'TXCH'
    
    # blob
    #   enum CommonModel::Serialization::Tags::Enum
    Modl = 0x4D6F646C # 'Modl'
    Skel = 0x536B656C # 'Skel'
    MatI = 0x4D617449 # 'MatI'
    Mesh = 0x4D657368 # 'Mesh'
    VLay = 0x564C6179 # 'VLay'
    IndB = 0x496E6442 # 'IndB'
    VerB = 0x56657242 # 'VerB'
    MBuf = 0x4D427566 # 'MBuf'

    MATI = 0x4D415449
    MATL = 0x4D41544C
    MTPR = 0x4D545052 # 'MTPR'
    DFPR = 0x44465052

    TXCB = 0x54584342 # 'TXCB'

class Version:
    def __init__(self):
        self.value = (0, 0)
    
    def deserialize(self, stream: BinaryStream):
        major = stream.read_u8()
        minor = stream.read_u8()
        self.value = (major, minor)
    
    def serialize(self, stream: BinaryStream):
        stream.write_u8(self.value[0])
        stream.write_u8(self.value[1])

    def __lt__(self, value: tuple[int, int]):
        return self.value < value

    def __le__(self, value: tuple[int, int]): # bool Bundle::BlobTag::IsAtMostVersion(uint8_t,uint8_t)
        return self.value <= value

    def __gt__(self, value: tuple[int, int]):
        return self.value > value
    
    def __ge__(self, value: tuple[int, int]): # bool Bundle::BlobTag::IsAtLeastVersion(uint8_t,uint8_t)
        return self.value >= value
    
    def __str__(self):
        return F"{self.version[0]}.{self.version[1]}"

# TODO: Metadata, Blob serialize/deserialize only ready header?
#   read data and structure in Bundle
#   sounds bad, maybe better separate headers into specific Header classes?
class Metadata:
    def __init__(self):
        self.tag = 0
        self.version = 0 # max: 0xF
        self.data_stream = None # max size: 0xFFF
    
    def deserialize(self, stream: BinaryStream):
        header_offset = stream.tell()

        self.tag = stream.read_u32()
        version_and_size = stream.read_u16()
        self.version = version_and_size & 0xF
        data_size = version_and_size >> 4
        data_offset = stream.read_u16() + header_offset
        with stream.scoped_seek(data_offset):
            self.data_stream = BinaryStream.from_buffer(stream.read_big(data_size))
    
    def serialize_header(self, stream: BinaryStream):
        stream.write_u32(self.tag)
        stream.write_u16(self.version | (self.data_stream.size() << 4))
        stream.write_u16(0xFFFF)

    def serialize_header_data_offset(self, stream: BinaryStream, data_offset: int):
        header_offset = stream.tell()

        stream.seek(6, os.SEEK_CUR)
        stream.write_u16(data_offset - header_offset)

    # TODO: def header_size(self): return 8 # for the 1st pass of serialization

    def read_string(self): # void Bundle::BlobReader::ReadMetaData(unsigned short, std::string &)
        if self.version > 0:
            print(F"Warning: Unsupported 'Name' metadata version. Found: {self.version}. Max supported: 0")
        return self.data_stream.read().decode('utf-8')
    
    def read_s32(self):
        if self.version > 0:
            print(F"Warning: Unsupported 'Id  ' metadata version. Found: {self.version}. Max supported: 0")
        return self.data_stream.read_s32()

class Blob:
    def __init__(self):
        self.tag = 0
        self.version = Version()
        self.metadata: dict[int, Metadata] = {}
        self.data_stream = None
    
    def deserialize(self, stream: BinaryStream):
        self.tag = stream.read_u32()
        self.version.deserialize(stream)
        metadata_length = stream.read_u16()
        metadata_offset = stream.read_u32()
        data_offset = stream.read_u32()
        data_size = stream.read_u32()
        stream.seek(4, os.SEEK_CUR)
        with stream.scoped_seek(metadata_offset):
            for _ in range(metadata_length):
                metadata = Metadata()
                metadata.deserialize(stream)
                self.append_metadata(metadata)
        with stream.scoped_seek(data_offset):
            self.data_stream = BinaryStream.from_buffer(stream.read_big(data_size))

    def serialize_header(self, stream: BinaryStream):
        stream.write_u32(self.tag)
        self.version.serialize(stream)
        stream.write_u16(len(self.metadata))
        stream.write_u32(0xFFFFFFFF)
        stream.write_u32(0xFFFFFFFF)
        data_size = self.data_stream.size()
        stream.write_u32(data_size)
        stream.write_u32(data_size)

    def serialize_header_metadata_offset(self, stream: BinaryStream, metadata_offset: int):
        stream.seek(8, os.SEEK_CUR)
        stream.write_u32(metadata_offset)

    def serialize_header_data_offset(self, stream: BinaryStream, data_offset: int):
        stream.seek(12, os.SEEK_CUR)
        stream.write_u32(data_offset)

    def serialize_metadata(self, stream: BinaryStream):
        metadata_offsets = [None] * len(self.metadata)
        for j, metadata in enumerate(self.metadata.values()):
            metadata_offsets[j] = stream.tell()
            metadata.serialize_header(stream)
        for j, metadata in enumerate(self.metadata.values()):
            metadata_data_offset = stream.tell()
            with stream.scoped_seek(metadata_offsets[j]):
                metadata.serialize_header_data_offset(stream, metadata_data_offset)
            stream.write(metadata.data_stream.getbuffer())

    def get_tag_string(self):
        # return chr((self.tag >> 24) & 0xFF) + chr((self.tag >> 16) & 0xFF) + chr((self.tag >> 8) & 0xFF) + chr(self.tag & 0xFF)
        return F"{(self.tag >> 24) & 0xFF:c}{(self.tag >> 16) & 0xFF:c}{(self.tag >> 8) & 0xFF:c}{self.tag & 0xFF:c}"

    def append_metadata(self, metadata: Metadata):
        self.metadata[metadata.tag] = metadata

    def remove_metadata(self, metadata: Metadata):
        del self.metadata[metadata.tag]

# @dataclass
class Bundle:
    def __init__(self):
        self.tag = 0
        self.version = Version()
        # TODO: replace list with set? each Blob is unique?
        self.blobs_groups: defaultdict[int, list[Blob]] = defaultdict(list) # std::unordered_multimap<uint32_t, Blob>
    
    def deserialize(self, stream: BinaryStream):
        self.tag = stream.read_u32()
        if self.tag != Tag.Grub:
            print("Warning: Bundle has invalid tag. Expected 'Grub'.")
        self.version.deserialize(stream)
        if self.version > (1, 1):
            print(F"Warning: Unsupported Bundle version. Found: {self.version}. Max supported: 1.1")
        if  self.version < (1, 0):
            print(F"Warning: Unsupported Bundle version. Found: {self.version}. Min supported: 1.0")
        blobs_length = stream.read_u16()
        stream.seek(4 * 2, os.SEEK_CUR)
        if self.version >= (1, 1):
            blobs_length = stream.read_u32()
        for _ in range(blobs_length):
            blob = Blob()
            blob.deserialize(stream)
            self.append_blob(blob)

    def serialize_header(self, stream: BinaryStream, blobs_length):
        stream.write_u32(self.tag)
        self.version.serialize(stream)
        stream.write(b"\x00\x00")
        stream.write_u32(0xFFFFFFFF)
        stream.write_u32(0xFFFFFFFF)
        stream.write_u32(blobs_length)

    def serialize_header_header_size(self, stream: BinaryStream, header_size: int):
        stream.seek(8, os.SEEK_CUR)
        stream.write_u32(header_size)

    def serialize_header_total_size(self, stream: BinaryStream, total_size: int):
        stream.seek(12, os.SEEK_CUR)
        stream.write_u32(total_size)

    def serialize(self, stream: BinaryStream):
        # TODO: calculate all offsets first, then write in 2nd pass
        header_offset = stream.tell()

        blobs = [blob for blobs_group in self.blobs_groups.values() for blob in blobs_group]

        self.serialize_header(stream, len(blobs))

        blobs_offsets = [None] * len(blobs)
        for i, blob in enumerate(blobs):
            blobs_offsets[i] = stream.tell()
            blob.serialize_header(stream)
        for i, blob in enumerate(blobs):
            metadata_offset = stream.tell() - header_offset
            with stream.scoped_seek(blobs_offsets[i]):
                blob.serialize_header_metadata_offset(stream, metadata_offset)
            blob.serialize_metadata(stream)

        stream.write_padding(4)

        header_size = stream.tell() - header_offset
        with stream.scoped_seek(header_offset):
            self.serialize_header_header_size(stream, header_size)

        for i, blob in enumerate(blobs):
            data_offset = stream.tell() - header_offset
            with stream.scoped_seek(blobs_offsets[i]):
                blob.serialize_header_data_offset(stream, data_offset)
            stream.write(blob.data_stream.getbuffer())

            stream.write_padding(4)

        total_size = stream.tell() - header_offset
        with stream.scoped_seek(header_offset):
            self.serialize_header_total_size(stream, total_size)

    def append_blob(self, blob: Blob):
        self.blobs_groups[blob.tag].append(blob)

    def remove_blob(self, blob: Blob):
        self.blobs_groups[blob.tag].remove(blob)

# CommonModel module; commonmodel:Unity_CommonModel_000.obj
class VertexBufferUsage: # CommonModel::Serialization::VBuffUsage
    def __init__(self):
        self.id = 0
        self.input_slot = 0
        self.stride = 0
        self.offset = 0

    def deserialize(self, stream: BinaryStream):
        self.id = stream.read_s32()
        self.input_slot = stream.read_s32()
        self.stride = stream.read_s32()
        self.offset = stream.read_s32()

    def serialize(self, stream: BinaryStream):
        stream.write_s32(self.id)
        stream.write_s32(self.input_slot)
        stream.write_s32(self.stride)
        stream.write_s32(self.offset)

class Mesh: # CommonModel::Mesh
    def __init__(self):
        self.material_id = 0
        self.bone_index = 0
        self.levels_of_detail = 0
        self.render_pass = 0
        self.skinning_elements_count = 0
        self.morph_weights_count = 0
        self.index_buffer_id = 0
        self.start_index_location = 0
        self.base_vertex_location = 0
        self.index_count = 0
        self.face_count = 0
        self.vertex_buffer_indices: list[VertexBufferUsage] = None
        self.uv_transforms: list[tuple[tuple[float, float], tuple[float, float]]] = [None] * 5
        self.scale: tuple[float, float, float, float] = (0, 0, 0, 0)
        self.translate: tuple[float, float, float, float] = (0, 0, 0, 0)
    
    # two functions: deserialize(stream) and load(blob) ?
    def deserialize(self, blob: Blob):
        if blob.version > (1, 9):
            print(F"Warning: Unsupported 'Mesh' blob version. Found: {blob.version}. Max supported: 1.9")
        if blob.version < (1, 0):
            print(F"Warning: Unsupported 'Mesh' blob version. Found: {blob.version}. Min supported: 1.0")

        self.name = blob.metadata[Tag.Name].read_string()

        self.material_id = blob.data_stream.read_s16()
        if blob.version >= (1, 9):
            self.unk1 = blob.data_stream.read(2 * 3)
        self.bone_index = blob.data_stream.read_s16()
        self.levels_of_detail = blob.data_stream.read_u16()
        self.lowest_level_of_detail = blob.data_stream.read_u8()
        self.highest_level_of_detail = blob.data_stream.read_u8()
        self.render_pass = blob.data_stream.read_u16()
        # if blob.version < (1, 7):
        #     self.render_pass |= 0x18
        self.unk3 = blob.data_stream.read(1)
        if blob.version >= (1, 2):
            self.skinning_elements_count = blob.data_stream.read_u8()
            self.morph_weights_count = blob.data_stream.read_u8()
        if blob.version >= (1, 3):
            self.unk5 = blob.data_stream.read(1)
        self.unk6 = blob.data_stream.read(1 + 2)
        self.index_buffer_id = blob.data_stream.read_s32()
        self.unk7 = blob.data_stream.read(4)
        self.start_index_location = blob.data_stream.read_s32()
        self.base_vertex_location = blob.data_stream.read_s32()
        self.index_count = blob.data_stream.read_u32()
        self.face_count = blob.data_stream.read_u32()
        if blob.version >= (1, 6):
            self.unk9 = blob.data_stream.read(4 + 4)
        self.vertex_layout_id = blob.data_stream.read_u32()
        self.vertex_buffer_indices_length = blob.data_stream.read_u32()
        self.vertex_buffer_indices = [None] * self.vertex_buffer_indices_length
        for _ in range(self.vertex_buffer_indices_length):
            vertex_buffer_index = VertexBufferUsage()
            vertex_buffer_index.deserialize(blob.data_stream)
            self.vertex_buffer_indices[vertex_buffer_index.input_slot] = vertex_buffer_index
        if blob.version >= (1, 4):
            self.morph_data_buffer_id = blob.data_stream.read_s32()
            self.skinning_data_buffer_id = blob.data_stream.read_s32()
        self.constant_buffer_indices_length = blob.data_stream.read_u32()
        if self.constant_buffer_indices_length != 0:
            print("Warning: Mesh.constant_buffer_indices_length != 0. Please report it in GitHub issue.")
            # throw exception
        if blob.version >= (1, 1):
            self.unk11 = blob.data_stream.read(4)
        if blob.version >= (1, 5):
            for i in range(5):
                self.uv_transforms[i] = ((blob.data_stream.read_f32(), blob.data_stream.read_f32()), (blob.data_stream.read_f32(), blob.data_stream.read_f32()))
        if blob.version >= (1, 8):
            self.scale = (blob.data_stream.read_f32(), blob.data_stream.read_f32(), blob.data_stream.read_f32(), blob.data_stream.read_f32())
            self.translate = (blob.data_stream.read_f32(), blob.data_stream.read_f32(), blob.data_stream.read_f32(), blob.data_stream.read_f32())

    def serialize(self, blob: Blob):
        blob.data_stream = BinaryStream(io.BytesIO())
        blob.data_stream.write_s16(self.material_id)
        if blob.version >= (1, 9):
            blob.data_stream.write(self.unk1)
        blob.data_stream.write_s16(self.bone_index)
        blob.data_stream.write_u16(self.levels_of_detail)
        blob.data_stream.write_u8(self.lowest_level_of_detail)
        blob.data_stream.write_u8(self.highest_level_of_detail)
        blob.data_stream.write_u16(self.render_pass)
        # if blob.version < (1, 7):
        #     self.render_pass &= ~0x18 # ?
        blob.data_stream.write(self.unk3)
        if blob.version >= (1, 2):
            blob.data_stream.write_u8(self.skinning_elements_count)
            blob.data_stream.write_u8(self.morph_weights_count)
        if blob.version >= (1, 3):
            blob.data_stream.write(self.unk5)
        blob.data_stream.write(self.unk6)
        blob.data_stream.write_s32(self.index_buffer_id)
        blob.data_stream.write(self.unk7)
        blob.data_stream.write_s32(self.start_index_location)
        blob.data_stream.write_s32(self.base_vertex_location)
        blob.data_stream.write_u32(self.index_count)
        blob.data_stream.write_u32(self.face_count)
        if blob.version >= (1, 6):
            blob.data_stream.write(self.unk9)
        blob.data_stream.write_u32(self.vertex_layout_id)
        blob.data_stream.write_u32(self.vertex_buffer_indices_length)
        for vertex_buffer_usage in self.vertex_buffer_indices:
            vertex_buffer_usage.serialize(blob.data_stream)
        if blob.version >= (1, 4):
            blob.data_stream.write_s32(self.morph_data_buffer_id)
            blob.data_stream.write_s32(self.skinning_data_buffer_id)
        blob.data_stream.write_u32(self.constant_buffer_indices_length)
        if blob.version >= (1, 1):
            blob.data_stream.write(self.unk11)
        if blob.version >= (1, 5):
            for uv_transform in self.uv_transforms:
                for values in uv_transform:
                    for value in values:
                        blob.data_stream.write_f32(value)
        if blob.version >= (1, 8):
            for value in self.scale:
                blob.data_stream.write_f32(value)
            for value in self.translate:
                blob.data_stream.write_f32(value)

class ModelBuffer: # CommonModel::ModelBuffer
    def __init__(self):
        self.length = 0
        self.size = 0
        self.stride = 0
        self.format = 0
        self.unk0 = b"\x00\x00"
        self.data: ByteString = None
    
    def deserialize(self, blob: Blob):
        self.length = blob.data_stream.read_u32()
        self.size = blob.data_stream.read_u32()
        self.stride = blob.data_stream.read_u16()
        self.unk0 = blob.data_stream.read(2)
        if blob.version >= (1, 0):
            self.format = blob.data_stream.read_u32()
        self.data = blob.data_stream.read_big(self.size)

    def serialize(self, blob: Blob):
        blob.data_stream = BinaryStream(io.BytesIO())
        blob.data_stream.write_u32(self.length)
        blob.data_stream.write_u32(self.size)
        blob.data_stream.write_u16(self.stride)
        blob.data_stream.write(self.unk0)
        if blob.version >= (1, 0):
            blob.data_stream.write_u32(self.format)
        blob.data_stream.write(self.data)

    def set_data(self, data: ByteString): # TODO: Py3.12 replace ByteString with Buffer
        self.size = len(data)
        self.length = self.size // self.stride
        self.data = data