from pathlib import Path
from .pvs_util import *

game_series = 0 # 0 - auto, 1 - Motorsport, 2 - Horizon

class PVSHeader:
    def __init__(self, version: int):
        self.version = version

    @staticmethod
    def from_stream(stream: BinaryStream):
        global game_series

        magic = stream.read_u32()
        if magic != 0x46505653: # 'FPVS'
            raise RuntimeError("Wrong magic number.")
        version = stream.read_u32()

        # game series selection heuristics
        if game_series == 0:
            game_series = 2 if version >= 45 else 1

        # the template supports much more versions, but you can implement only FM3 support and add more versions later if neccessary
        if game_series == 1:
            min_version = 23
            max_version = 27
        elif game_series == 2:
            min_version = 45
            max_version = 51
        if version > max_version:
            print(F"Warning: Unsupported PVS version. Found: {version}. Max supported: {max_version}")
        if version < min_version:
            print(F"Warning: Unsupported PVS version. Found: {version}. Min supported: {min_version}")

        stream.skip(4) # just skip fields if you don't need them
        if version >= 27:
            stream.skip(4)
        return PVSHeader(version)

class ModelInstanceDetails:
    def __init__(self, transform: list[list[int]], material_data: float):
        self.transform = transform
        self.material_data = material_data

    @staticmethod
    def from_stream(stream: BinaryStream, version: int):
        stream.skip(6)
        t = [stream.read_f32() for _ in range(3)]
        r = [[stream.read_f16() for _ in range(3)] for _ in range(3)]
        transform = [
            [r[0][0], r[1][0], r[2][0], t[0]],
            [r[0][1], r[1][1], r[2][1], t[1]],
            [r[0][2], r[1][2], r[2][2], t[2]],
            [0, 0, 0, 1]
        ]
        material_data = stream.read_f32()
        stream.skip(4 * 3)
        use_dynamic_3d_data = stream.read_u8() != 0
        if use_dynamic_3d_data:
            stream.skip(4)
            routes_length = stream.read_u8()
            if version >= 51:
                stream.skip(2 * routes_length)
            else:
                stream.skip(routes_length)
            stream.skip(32)
        return ModelInstanceDetails(transform, material_data)

class PVSZone:
    def __init__(self, model_instance_indexes: list[int], model_instance_details: list[ModelInstanceDetails] | None):
        self.model_instance_indexes = model_instance_indexes
        self.model_instance_details = model_instance_details

    # we need this class, because this file format is sequential and this structure contain variable length fields
    # se we have to read at least the length fields to calculate how much bytes we should skip
    @staticmethod
    def from_stream(stream: BinaryStream, version: int, tools_based_zone_unioning: bool):
        model_instance_indexes_length = stream.read_u32()
        if game_series == 2:
            model_instance_indexes = [stream.read_u32() for _ in range(model_instance_indexes_length)]
        else:
            model_instance_indexes = [stream.read_u16() for _ in range(model_instance_indexes_length)]
        if game_series == 2 and tools_based_zone_unioning:
            length = stream.read_u32()
            stream.skip(2 * length)
            length = stream.read_u32()
            stream.skip(16 * length)
            length = stream.read_u32()
            stream.skip(4 * length)
            length = stream.read_u32()
            stream.skip(length)
        unk2_length = stream.read_u32()
        stream.skip(2 * unk2_length)
        textures_references_length = stream.read_u32()
        stream.skip(4 * textures_references_length)
        textures_use_length = stream.read_u32()
        stream.skip(textures_use_length)
        if game_series == 2:
            length = stream.read_u32()
            stream.skip(16 * length)
            length = stream.read_u32()
            stream.skip(length)
            model_instance_details_length = stream.read_u32()
            model_instance_details = [ModelInstanceDetails.from_stream(stream, version) for _ in range(model_instance_details_length)]
        else:
            model_instance_details = None
        return PVSZone(model_instance_indexes, model_instance_details)

class PVSModelInstance:
    def __init__(self, model_index: int, parent_lod_model_instance_offset: int, flags: int, texture: int, model_data: float | None, transform: list[list[float]] | None):
        self.model_index = model_index
        self.parent_lod_model_instance_offset = parent_lod_model_instance_offset
        self.flags = flags
        self.texture = texture
        self.model_data = model_data
        self.transform = transform

    @staticmethod
    def from_stream(stream: BinaryStream, version):
        model_index = stream.read_u16()
        if game_series == 2 and version >= 49:
            parent_lod_model_instance_offset = stream.read_s16()
        else:
            parent_lod_model_instance_offset = 0
        flags = stream.read_u32()
        texture = stream.read_u32()
        stream.skip(4)
        if game_series == 2:
            stream.skip(2)
            model_data = None
            # transform = None
            # place everything at Z +5000, overwritten by ModelInstanceDetails later
            transform = [
                [1, 0, 0, 0],
                [0, 1, 0, 5000],
                [0, 0, -1, 0],
                [0, 0, 0, 1],
            ]
        else:
            model_data = stream.read_f32()
            if version >= 25:
                stream.skip(4 * 3 + 2 * 3 + 2)
            else:
                stream.skip(2 * 3 + 2)
            t = [stream.read_f32() for _ in range(3)]
            r = [[stream.read_f16() for _ in range(3)] for _ in range(3)]
            transform = [
                [r[0][0], r[1][0], r[2][0], t[0]],
                [r[0][1], r[1][1], r[2][1], t[1]],
                [r[0][2], r[1][2], r[2][2], t[2]],
                [0, 0, 0, 1]
            ]
        return PVSModelInstance(model_index, parent_lod_model_instance_offset, flags, texture, model_data, transform)

class PVSModel:
    def __init__(self, model_index, textures, shaders):
        self.model_index = model_index
        self.textures = textures
        self.shaders = shaders

    @staticmethod
    def from_stream(stream: BinaryStream, model_index):
        textures_references_length = stream.read_u32()
        textures = [stream.read_u32() for _ in range(textures_references_length)]
        shader_length = stream.read_u32()
        shaders = [stream.read_u32() for _ in range(shader_length)]
        if game_series == 2:
            stream.skip(12 * 4 + 12)
        else:
            stream.skip(16 * 4 + 16)
        return PVSModel(model_index, textures, shaders)

class PVSTexture:
    def __init__(self, texture_file_name, index_in_stx_bin, u_scale, v_scale, u_translate, v_translate):
        self.texture_file_name = texture_file_name
        self.index_in_stx_bin = index_in_stx_bin
        self.u_scale = u_scale
        self.v_scale = v_scale
        self.u_translate = u_translate
        self.v_translate = v_translate

    @staticmethod
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
    def __init__(self, header: PVSHeader, models_instances: list[PVSModelInstance], models: list[PVSModel], textures: list[PVSTexture], shaders: list[str], sky_model_instance: PVSModelInstance | None, sky_model: PVSModel | None, lone_models_instances: list[PVSModelInstance], prefix: str):
        self.header = header
        self.models_instances = models_instances
        self.models = models
        self.textures = textures
        self.shaders = shaders
        self.sky_model_instance = sky_model_instance
        self.sky_model = sky_model
        self.lone_models_instances = lone_models_instances
        self.prefix = prefix

    @staticmethod
    def from_stream(stream: BinaryStream, bin_path: Path):
        header = PVSHeader.from_stream(stream) # type: ignore
        ribbon_index = stream.read_u16()
        tools_based_zone_unioning = False
        if game_series == 2:
            stream.skip(4 + 1)
            if header.version >= 47:
                tools_based_zone_unioning = stream.read_u8() != 0
            stream.skip(4)
            if header.version >= 46:
                stream.skip(4)
            if header.version >= 48:
                unk_length = stream.read_u32()
                stream.skip(4 * unk_length)
            stream.skip(1)
        stream.skip(2)
        zones_length = stream.read_u32()
        for _ in range(zones_length):
            PVSZone.from_stream(stream, header.version, tools_based_zone_unioning) # don't store since we don't need this structure yet
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
            if game_series == 2:
                stream.skip(4 * unk0_length)
            else:
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
        if game_series == 2:
            stream.skip(2)
            objects_id_length = stream.read_u32()
            for _ in range(objects_id_length):
                stream.read_string()
            zone_visibility_length = stream.read_u32()
            if zone_visibility_length != 0:
                raise RuntimeError()
            stream.skip(1)
            streamed_zones_length = stream.read_u32()
            for i in range(streamed_zones_length):
                # overwrite ModelInstance properties with ModelInstanceDetails from the first zone it appeared
                zone_path = bin_path / F"__R{ribbon_index:02d}Z{i:05d}.pvsz"
                zone = PVSZone.from_stream(BinaryStream.from_path(zone_path.resolve(), ">"), header.version, tools_based_zone_unioning)
                for index_bitfield, details in zip(zone.model_instance_indexes, zone.model_instance_details):
                    index = index_bitfield & 0x7FFFFFFF
                    if models_instances[index].model_data is None:
                        models_instances[index].model_data = details.material_data
                        models_instances[index].transform = details.transform
                    elif models_instances[index].model_data != details.material_data or models_instances[index].transform != details.transform:
                        raise RuntimeError()

                # # copy properties from a lower LOD, if LOD0 never appeared in zones
                # for i, model_instance in enumerate(models_instances):
                #     if model_instance.model_data is None and model_instance.parent_lod_model_instance_offset != 0:
                #         parent_model_instance = model_instance
                #         j = i
                #         for _ in range(2):
                #             # walk from lowest to highest LOD
                #             j += parent_model_instance.parent_lod_model_instance_offset
                #             parent_model_instance = models_instances[j]
                #             if parent_model_instance.transform is None:
                #                 continue
                #             model_instance.transform = parent_model_instance.transform
        return PVS(header, models_instances, models, textures, shaders, sky_model_instance, sky_model, lone_models_instances, prefix)
