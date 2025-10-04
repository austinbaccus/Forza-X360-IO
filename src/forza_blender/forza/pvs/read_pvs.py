from .pvs_util import *
import mathutils

class PVSHeader:
    def __init__(self, version: int):
        self.version = version

    def from_stream(stream: BinaryStream):
        magic = stream.read_u32()
        if magic != 0x46505653: # 'FPVS'
            raise RuntimeError("Wrong magic number.")
        version = stream.read_u32()
        # the template supports much more versions, but you can implement only FM3 support and add more versions later if neccessary
        if version > 24:
            print(F"Warning: Unsupported PVS version. Found: {version}. Max supported: 24")
        if version < 24:
            print(F"Warning: Unsupported PVS version. Found: {version}. Min supported: 24")
        stream.skip(4) # just skip fields if you don't need them
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
    def __init__(self, model_index: int, translate_x = None, translate_y = None, translate_z = None, matrix_world = None):
        self.model_index = model_index
        self.position = (0,0,0)
        if translate_x is not None and translate_y is not None and translate_z is not None:
            self.position = (translate_x,-translate_z,translate_y)
        self.rotation = (0,0,0)
        self.matrix_world = None
        if matrix_world is not None:
            self.matrix_world = matrix_world
        self.scale = (0,0,0)

    def from_stream(stream: BinaryStream):
        model_index = stream.read_u16()
        stream.skip(24)
        
        translate_x: float = stream.read_f32()
        translate_y: float = stream.read_f32()
        translate_z: float = -stream.read_f32()

        r0 = (stream.read_f16(),stream.read_f16(),stream.read_f16())
        r1 = (stream.read_f16(),stream.read_f16(),stream.read_f16())
        r2 = (stream.read_f16(),stream.read_f16(),stream.read_f16())

        matrix_world = mathutils.Matrix((r0, r1, r2))
        if r0[0] == 1 and r0[1] == 0 and r0[2] == 0:
            if r1[0] == 0 and r1[1] == 1 and r1[2] == 0:
                if r2[0] == 0 and r2[1] == 0 and r2[2] == -1:
                    matrix_world = None # if it's one of the pvs_model_instances with a "blank" rotation matrix, don't do anything
                
        return PVSModelInstance(model_index, translate_x, translate_y, translate_z, matrix_world)

class PVSModel:
    # same here, some work needs to be done
    def from_stream(stream: BinaryStream):
        textures_references_length = stream.read_u32()
        stream.skip(4 * textures_references_length)
        unk2_length = stream.read_u32()
        stream.skip(4 * unk2_length + 64 + 16)

class PVS:
    # fill this in with stuff like texture references, transforms, translations, etc.
    def __init__(self, header: PVSHeader, models_instances: list[PVSModelInstance], models: list[PVSModel]):
        self.header = header
        self.models_instances = models_instances
        self.models = models

    def from_stream(stream: BinaryStream):
        header = PVSHeader.from_stream(stream)
        stream.skip(2 + 2)
        zones_length = stream.read_u32()
        for _ in range(zones_length):
            PVSZone.from_stream(stream) # don't store since we don't need this structure yet
        textures_length = stream.read_u32()
        stream.skip(28 * textures_length) # TODO: make PVSTexture class
        shaders_length = stream.read_u32()
        for _ in range(shaders_length):
            stream.read_string() # a string with 32-bit size prefix
        models_instances_length = stream.read_u32()
        models_instances = [PVSModelInstance.from_stream(stream) for _ in range(models_instances_length)]
        models_length = stream.read_u32()
        models = [PVSModel.from_stream(stream) for _ in range(models_length)]
        return PVS(header, models_instances, models)