from forza_blender.forza.pvs.pvs_util import BinaryStream
from .forza_track_section import ForzaTrackSection

class RmbBin:
    def __init__(self, path_file):
        self.path_file = path_file
        self.track_sections = []
        self.shader_filenames = []

    def populate_objects_from_rmbbin(self):
        stream = BinaryStream.from_path(self.path_file, ">")

        self.version = stream.read_u32()

        stream.skip(112)

        # read SubModel_Container section
        track_sections_count: int = stream.read_u32()
        self.track_sections = [ForzaTrackSection(stream) for _ in range(track_sections_count)]

        # read MaterialSets_Container section
        stream.skip(4) # version
        material_sets_container_count: int = stream.read_u32()
        for i in range(material_sets_container_count):
            stream.skip(8) # MaterialSet version, Container version
            material_container_count: int = stream.read_u32()
            for j in range(material_container_count):
                stream.skip(12) # version, fxfilenameindex, techniqueindex

                # VertexShaderConstants_Container
                stream.skip(4) # version
                length: int = stream.read_u32()
                vertex_shader_constants = [[stream.read_f32() for _ in range(4)] for _ in range(length)]
                #stream.skip(length*16)

                # PixelShaderConstants_Container
                stream.skip(4) # version
                length: int = stream.read_u32()
                stream.skip(length*16)

                # TextureSamplerIndices_Container
                stream.skip(4) # version
                length: int = stream.read_u32()
                stream.skip(length*4)

        # read FxFileNames section
        stream.skip(4) # version
        fx_filenames_count: int = stream.read_u32()
        self.shader_filenames = [stream.read_string() for _ in range(fx_filenames_count)]
