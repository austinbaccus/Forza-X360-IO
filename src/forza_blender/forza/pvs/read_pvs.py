from .pvs_util import *

class PVSHeader:
    def __init__(self, version: int):
        self.version = version

    def from_stream(stream: BinaryStream):
        magic = stream.read_u32()
        if magic != 0x46505653: # 'FPVS'
            raise RuntimeError("Wrong magic number.")
        version = stream.read_u32()
        # the template supports much more versions, but you can implement only FM3 support and add more versions later if neccessary
        if version > 27:
            print(F"Warning: Unsupported PVS version. Found: {version}. Max supported: 27")
        if version < 24:
            print(F"Warning: Unsupported PVS version. Found: {version}. Min supported: 24")
        stream.skip(4) # just skip fields if you don't need them
        if version >= 27:
            stream.skip(4)
        return PVSHeader(version)

class PVSZone:
    # we need this class, because this file format is sequential and this structure contain variable length fields
    # se we have to read at least the length fields to calculate how much bytes we should skip
    def from_stream(stream: BinaryStream):
        unk1_length = stream.read_u32()
        stream.skip(2 * unk1_length) # skip array of uint16
        unk2_length = stream.read_u32()
        stream.skip(2 * unk2_length)
        textures_references_length = stream.read_u32()
        stream.skip(4 * textures_references_length)
        textures_use_length = stream.read_u32()
        stream.skip(textures_use_length)

class PVSModelInstance:
    def __init__(self, model_index: int, flags: int, texture: int, model_data: float, transform: list[list[float]]):
        self.model_index = model_index
        self.flags = flags
        self.texture = texture
        self.model_data = model_data
        self.transform = transform

    def from_stream(stream: BinaryStream, version):
        model_index = stream.read_u16()
        flags = stream.read_u32()
        texture = stream.read_u32()
        stream.skip(4)
        model_data = stream.read_f32()
        if version >= 25:
            stream.skip(20)
        else:
            stream.skip(8)
        
        translate_x: float = stream.read_f32()
        translate_y: float = stream.read_f32()
        translate_z: float = stream.read_f32()

        r0 = (stream.read_f16(),stream.read_f16(),stream.read_f16())
        r1 = (stream.read_f16(),stream.read_f16(),stream.read_f16())
        r2 = (stream.read_f16(),stream.read_f16(),stream.read_f16())

        transform = [
            [r0[0], r1[0], r2[0], translate_x],
            [r0[1], r1[1], r2[1], translate_y],
            [r0[2], r1[2], r2[2], translate_z],
            [0, 0, 0, 1]
        ]
        return PVSModelInstance(model_index, flags, texture, model_data, transform)

class PVSModel:
    def __init__(self, model_index, textures, shaders):
        self.model_index = model_index
        self.textures = textures
        self.shaders = shaders

    def from_stream(stream: BinaryStream, model_index):
        textures_references_length = stream.read_u32()
        textures = []
        for i in range(textures_references_length):
            textures.append(stream.read_u32())
        shader_length = stream.read_u32()
        shaders = []
        for i in range(shader_length):
            shaders.append(stream.read_u32())
        stream.skip(64 + 16)

        return PVSModel(model_index, textures, shaders)

class PVSTexture:
    def __init__(self, texture_file_name, index_in_stx_bin, u_scale, v_scale, u_translate, v_translate):
        self.texture_file_name = texture_file_name
        self.index_in_stx_bin = index_in_stx_bin
        self.u_scale = u_scale
        self.v_scale = v_scale
        self.u_translate = u_translate
        self.v_translate = v_translate
        
    def from_stream(stream: BinaryStream):
        texture_file_name = stream.read_u32()
        index_in_stx_bin = stream.read_u32()
        u_scale = stream.read_f32()
        v_scale = stream.read_f32()
        u_translate = stream.read_f32()
        v_translate = stream.read_f32()
        stream.skip(4)

        return PVSTexture(texture_file_name, index_in_stx_bin, u_scale, v_scale, u_translate, v_translate)

class PVS:
    def __init__(self, header: PVSHeader, models_instances: list[PVSModelInstance], models: list[PVSModel], textures: list[PVSTexture], shaders: list[str], sky_model_instance: PVSModelInstance, sky_model: PVSModel, lone_models_instances: list[PVSModelInstance], prefix: str):
        self.header = header
        self.models_instances = models_instances
        self.models = models
        self.textures = textures
        self.shaders = shaders
        self.sky_model_instance = sky_model_instance
        self.sky_model = sky_model
        self.lone_models_instances = lone_models_instances
        self.prefix = prefix

    def from_stream(stream: BinaryStream):
        header = PVSHeader.from_stream(stream) # type: ignore
        stream.skip(2 + 2)
        zones_length = stream.read_u32()
        for _ in range(zones_length):
            PVSZone.from_stream(stream) # don't store since we don't need this structure yet
        textures_length = stream.read_u32()
        textures = [PVSTexture.from_stream(stream) for _ in range(textures_length)]
        shaders_length = stream.read_u32()
        shaders = [stream.read_string() for _ in range(shaders_length)] # a string with 32-bit size prefix
        models_instances_length = stream.read_u32()
        models_instances = [PVSModelInstance.from_stream(stream, header.version) for _ in range(models_instances_length)]
        models_length = stream.read_u32()
        models = [PVSModel.from_stream(stream,idx) for idx in range(models_length)]
        if header.version >= 26:
            sky_model_instance = None
            sky_model = None
            unk0_length = stream.read_u32()
            stream.skip(2 * unk0_length)
            unk1_length = stream.read_u32()
            stream.skip(2 * unk1_length)
            unk2_length = stream.read_u32()
            stream.skip(2 * unk2_length)
        else:
            sky_model_instance = PVSModelInstance.from_stream(stream, header.version)
            sky_model = PVSModel.from_stream(stream, -1)
        lone_models_instances_length = stream.read_u32()
        lone_models_instances = [PVSModelInstance.from_stream(stream, header.version) for _ in range(lone_models_instances_length)]
        prefix = stream.read_string()
        return PVS(header, models_instances, models, textures, shaders, sky_model_instance, sky_model, lone_models_instances, prefix)
