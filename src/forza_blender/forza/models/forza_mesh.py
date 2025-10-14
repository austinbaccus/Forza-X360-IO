from forza_blender.forza.pvs.read_pvs import PVSTexture
from .forza_vertex import ForzaVertex

class ForzaMesh:
    def __init__(self, name: str, material_name: str, faces, vertices: ForzaVertex, material_indexes, track_bin, track_section, transform, model_index = None, textures = None, shader_filenames = None):
        self.name = name
        self.material_name = material_name
        self.faces = faces
        self.vertices = vertices
        self.material_indexes = material_indexes
        self.track_bin = track_bin
        self.track_section = track_section
        self.transform = transform
        self.model_index = model_index
        self.textures: list[PVSTexture] = textures

        self.track_section_index: int = None
        self.track_section_filename: str = None
        self.shader_index: int = None
        self.shader_filenames = shader_filenames

    def get_face_count(self):
        return len(self.faces)
    
    def get_vertext_count(self):
        return len(self.vertices)