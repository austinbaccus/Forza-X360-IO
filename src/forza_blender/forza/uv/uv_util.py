from forza_blender.forza.models import forza_mesh 

def generate_and_assign_uv_layers_to_object(obj, forza_mesh: forza_mesh.ForzaMesh):
    mesh = obj.data
    uv_layer1 = mesh.uv_layers.get("UVMap1") or mesh.uv_layers.new(name="UVMap1")
    uv_layer2 = mesh.uv_layers.get("UVMap2") or mesh.uv_layers.new(name="UVMap2")
    mesh.uv_layers.active = uv_layer1

    vert_uv1 = []
    vert_uv2 = []
    for v in forza_mesh.vertices:
        u1, v1 = float(v.texture0.x), float(v.texture0.y)
        u2, v2 = float(v.texture1.x), float(v.texture1.y)
        vert_uv1.append((u1, v1))
        vert_uv2.append((u2, v2))

    for li, loop in enumerate(mesh.loops):
        vi = loop.vertex_index
        # uv1
        if 0 <= vi < len(vert_uv1):
            uv_layer1.data[li].uv = vert_uv1[vi]
        else:
            uv_layer1.data[li].uv = (0.0, 0.0)
        # uv2
        if 0 <= vi < len(vert_uv2):
            uv_layer2.data[li].uv = vert_uv2[vi]
        else:
            uv_layer2.data[li].uv = (0.0, 0.0)

    mesh.update()