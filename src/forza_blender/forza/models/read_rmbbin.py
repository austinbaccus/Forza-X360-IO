import struct
from ..utils.forza_version import ForzaVersion
from .forza_track_section import ForzaTrackSection
from mathutils import Vector # type: ignore

class RmbBin:
    def __init__(self, path_file):
        self.forza_version: ForzaVersion = ForzaVersion.Unknown
        self.path_file = path_file
        self.track_sections = []
        self.shader_filenames = []

    def populate_objects_from_rmbbin(self):
        with self.path_file.open('rb') as f:
            _ = f.read(4)

            # TODO 
            # "int.from_bytes is made for a different thing. 
            # To parse file types from binary, struct.unpack is preferred" - Doliman100
            num = int.from_bytes(_, byteorder="big", signed=False)

            if num == 4:
                self.forza_version = ForzaVersion.FM3
            elif num == 6:
                self.forza_version = ForzaVersion.FM4

            f.read(112)

            # read SubModel_Container section
            track_sections_count: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
            for i in range(track_sections_count):
                self.track_sections.append(ForzaTrackSection(f))

            # read MaterialSets_Container section
            f.read(4) # version
            material_sets_container_count: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
            for i in range(material_sets_container_count):
                f.read(8) # version x2
                material_container_count: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
                for j in range(material_container_count):
                    f.read(12) # version, fxfilenameindex, techniqueindex

                    # VertexShaderConstants_Container
                    f.read(4) # version
                    length: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
                    vertex_shader_constants = []
                    for k in range(length):
                        vertex_shader_constants.append(Vector(struct.unpack(">4f", f.read(16))))
                    #f.read(length*16)

                    # PixelShaderConstants_Container
                    f.read(4) # version
                    length: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
                    f.read(length*16)

                    # TextureSamplerIndices_Container
                    f.read(4) # version
                    length: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
                    f.read(length*4)

            # read FxFileNames section
            f.read(4) # version
            fx_filenames_count: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
            for i in range(fx_filenames_count):
                shader_filename_length: int = int.from_bytes(f.read(4), byteorder="big", signed=False)
                shader_filename_bytes = f.read(shader_filename_length)
                shader_filename_str = str(shader_filename_bytes.decode("latin_1"))
                self.shader_filenames.append(shader_filename_str)
