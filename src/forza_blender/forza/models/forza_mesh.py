from .forza_vertex import ForzaVertex

class ForzaMesh:
    def __init__(self, name: str, material_name: str, indices: list[int], vertices: list[ForzaVertex], transform):
        self.name = name
        self.material_name = material_name
        self.indices = indices
        self.vertices = vertices
        self.transform = transform

    def get_face_count(self):
        return len(self.indices) / 3
    
    def get_vertext_count(self):
        return len(self.vertices)