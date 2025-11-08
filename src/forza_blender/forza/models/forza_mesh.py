from forza_blender.forza.pvs.read_pvs import PVSTexture
from .forza_vertex import ForzaVertex

class ForzaMesh:
    def __init__(self, name: str, material_name: str, faces, vertices: ForzaVertex, material_indexes, track_bin, track_section, textures: list[tuple[PVSTexture, int, bool]], shader_filenames, inherited_textures: list[int]):
        self.name = name
        self.material_name = material_name
        self.faces = faces
        self.vertices = vertices
        self.material_indexes = material_indexes
        self.track_bin = track_bin
        self.track_section = track_section
        self.textures = textures
        self.inherited_textures = inherited_textures

        self.track_section_index: int = None
        self.track_section_filename: str = None
        self.shader_index: int = None
        self.shader_filenames = shader_filenames

    def get_face_count(self):
        return len(self.faces)
    
    def get_vertext_count(self):
        return len(self.vertices)