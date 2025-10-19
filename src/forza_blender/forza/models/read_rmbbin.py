from forza_blender.forza.pvs.pvs_util import BinaryStream
from .forza_track_section import ForzaTrackSection

class Material:
    def __init__(self, fx_filename_index: int, texture_sampler_indices: list[int]):
        self.fx_filename_index = fx_filename_index
        self.texture_sampler_indices = texture_sampler_indices

    def from_stream(stream: BinaryStream):
        stream.skip(4) # version
        fx_filename_index = stream.read_u32()
        stream.skip(4) # techniqueindex

        # VertexShaderConstants_Container
        stream.skip(4) # version
        length = stream.read_u32()
        #vertex_shader_constants = [[stream.read_f32() for _ in range(4)] for _ in range(length)]
        stream.skip(16*length)

        # PixelShaderConstants_Container
        stream.skip(4) # version
        length = stream.read_u32()
        stream.skip(16*length)

        # TextureSamplerIndices_Container
        stream.skip(4) # version
        texture_sampler_indices_length = stream.read_u32()
        texture_sampler_indices = [stream.read_s32() for _ in range(texture_sampler_indices_length)]
        return Material(fx_filename_index, texture_sampler_indices)

class MaterialSet:
    def __init__(self, materials: list[Material]):
        self.materials = materials

    def from_stream(stream: BinaryStream):
        stream.skip(8) # MaterialSet version, Container version
        materials_length: int = stream.read_u32()
        materials = [Material.from_stream(stream) for _ in range(materials_length)]
        return MaterialSet(materials)

class RmbBin:
    def __init__(self, path_file: str, version: int, track_sections: list[ForzaTrackSection], material_sets: list[MaterialSet], shader_filenames: list[str]):
        self.path_file = path_file
        self.version = version
        self.track_sections = track_sections
        self.material_sets = material_sets
        self.shader_filenames = shader_filenames

    def from_path(path_file: str):
        stream = BinaryStream.from_path(path_file, ">")

        version = stream.read_u32()

        stream.skip(112)

        # read SubModel_Container section
        track_sections_count: int = stream.read_u32()
        track_sections = [ForzaTrackSection.from_stream(stream) for _ in range(track_sections_count)]

        # read MaterialSets_Container section
        stream.skip(4) # version
        material_sets_length: int = stream.read_u32()
        material_sets = [MaterialSet.from_stream(stream) for _ in range(material_sets_length)]

        # read FxFileNames section
        stream.skip(4) # version
        fx_filenames_count: int = stream.read_u32()
        shader_filenames = [stream.read_string() for _ in range(fx_filenames_count)]
        return RmbBin(path_file, version, track_sections, material_sets, shader_filenames)
