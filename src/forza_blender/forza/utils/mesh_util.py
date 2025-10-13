import numpy as np
from forza_blender.forza.models.forza_mesh import ForzaMesh
import bpy # type: ignore

def generate_triangle_list(indices, reset_index: int):
    a = indices[:-2]
    b = indices[1:-1]
    c = indices[2:]
    tris = np.stack((a, b, c), axis=1)
    swap_mask = [None] * a.shape[0]
    is_even = False
    for i, index in enumerate(a):
        swap_mask[i] = is_even
        is_even = not is_even and index != reset_index
    tris[swap_mask, :2] = tris[swap_mask, 1::-1]
    return tris[(tris != reset_index).all(axis=1)]

def convert_forzamesh_into_blendermesh(forza_mesh: ForzaMesh):
    vertices = forza_mesh.vertices.position
    faces = forza_mesh.faces
    mesh = bpy.data.meshes.new(name=forza_mesh.name)
    mesh.from_pydata(vertices, [], faces, False)
    mesh.validate()
    return mesh