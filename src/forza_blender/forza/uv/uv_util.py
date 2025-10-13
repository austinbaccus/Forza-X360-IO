import numpy as np
from forza_blender.forza.models import forza_mesh 

def generate_and_assign_uv_layers_to_object(obj, forza_mesh: forza_mesh.ForzaMesh):
    mesh = obj.data

    for i, texcoord in enumerate(forza_mesh.vertices.texcoords):
        if texcoord is None:
            continue
        uv_layer_name = F"TEXCOORD{i}"
        uv_layer = mesh.uv_layers.get(uv_layer_name) or mesh.uv_layers.new(name=uv_layer_name)
        # can't use indexes from ForzaMesh, because Blender might remove bad faces
        indexes = np.empty(len(mesh.loops), np.uint32)
        mesh.loops.foreach_get("vertex_index", indexes)
        uv_layer.uv.foreach_set("vector", texcoord[indexes].ravel())
