from forza_blender.forza.pvs.read_pvs import PVSTexture
from .forza_vertex import ForzaVertex

class ForzaMesh:
    def __init__(self, name: str, material_name: str, indices: list[int], vertices: list[ForzaVertex], transform, model_index = None, textures = None, texture_indices: list[int] = None):
        self.name = name
        self.material_name = material_name # TODO: is this the shader?
        self.indices = indices
        self.vertices = vertices
        self.transform = transform
        self.model_index = model_index
        self.textures: list[PVSTexture] = textures
        self.texture_indices = texture_indices
        self.shaders = None

    def get_face_count(self):
        return len(self.indices) / 3
    
    def get_vertext_count(self):
        return len(self.vertices)