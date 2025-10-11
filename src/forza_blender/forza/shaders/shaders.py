import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.textures.texture_util import get_image_from_index

def generate_blender_materials_for_mesh(forza_mesh: ForzaMesh, forza_last_texture_folder):
    materials = []
    for shader_filename in forza_mesh.shader_filenames:
        shader_filename_simple = (shader_filename.split('\\')[-1]).split('.')[0]
        if "diff_spec_1" == shader_filename_simple:
            materials.append(_DIFF_SPEC_1(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_opac_2" == shader_filename_simple:
            materials.append(_DIFF_OPAC_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_spec_opac_refl_3" == shader_filename_simple:
            materials.append(_DIFF_SPEC_OPAC_REFL_3(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "road_blnd_2" == shader_filename_simple:
            materials.append(_ROAD_BLND_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "road_diff_spec_ovly_blur_detailscale_2" == shader_filename_simple:
            materials.append(_ROAD_DIFF_SPEC_OVLY_BLUR_DETAILSCALE_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        else:
            materials.append(_UNKNOWN_SHADER(forza_mesh, forza_last_texture_folder, shader_filename_simple))
    return materials

def _UNKNOWN_SHADER(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = []
    for texture in forza_mesh.textures:
        texture_img = get_image_from_index(path_last_texture_folder, texture.texture_file_name)
        images.append(texture_img)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage"); tex.image = images[0]; tex.location = (-600, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0)
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        #links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    x = -600
    y = -300
    for img in images[1:]:
        tex_extra = nodes.new("ShaderNodeTexImage"); tex_extra.image = img; tex_extra.location = (x, y)
        y = y - 300

    return mat

def _DIFF_OPAC_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = []
    for texture in forza_mesh.textures:
        texture_img = get_image_from_index(path_last_texture_folder, texture.texture_file_name)
        images.append(texture_img)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage"); tex.image = images[0]; tex.location = (-600, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0)
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    x = -600
    y = -300
    for img in images[1:]:
        tex_extra = nodes.new("ShaderNodeTexImage"); tex_extra.image = img; tex_extra.location = (x, y)
        y = y - 300

    return mat

def _DIFF_SPEC_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = []
    for texture in forza_mesh.textures:
        texture_img = get_image_from_index(path_last_texture_folder, texture.texture_file_name)
        images.append(texture_img)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        diffuse_node = nodes.new("ShaderNodeTexImage"); diffuse_node.image = images[0]; diffuse_node.location = (-600, 0)
        ambient_occlusion_node = nodes.new("ShaderNodeTexImage"); ambient_occlusion_node.image = images[1]; ambient_occlusion_node.location = (-600, -300)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (-300, 150)
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "UVMap2"; uv_map_node.location = (-900, -300)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (0, 0)
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (300, 0)

        # link
        links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    x = -600
    y = -600
    for img in images[2:]:
        tex_extra = nodes.new("ShaderNodeTexImage"); tex_extra.image = img; tex_extra.location = (x, y)
        y = y - 300

    return mat

def _DIFF_SPEC_OPAC_REFL_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    return _UNKNOWN_SHADER(forza_mesh, path_last_texture_folder, shader_name)

def _ROAD_BLND_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    return _UNKNOWN_SHADER(forza_mesh, path_last_texture_folder, shader_name)

def _ROAD_DIFF_SPEC_OVLY_BLUR_DETAILSCALE_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = []
    for texture in forza_mesh.textures:
        texture_img = get_image_from_index(path_last_texture_folder, texture.texture_file_name)
        images.append(texture_img)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()

        diffuse1_node = nodes.new("ShaderNodeTexImage"); diffuse1_node.image = images[0]; diffuse1_node.location = (-600, 0)
        diffuse2_node = nodes.new("ShaderNodeTexImage"); diffuse2_node.image = images[1]; diffuse2_node.location = (-600, -300)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (-300, 150)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (4.0, 16.0, 1.0); map_node.location = (-900, -300)
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord')

        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (0, 0)
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (300, 0)

        # link
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(map_node.outputs[0], diffuse1_node.inputs["Vector"])
        links.new(diffuse1_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(diffuse2_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], bsdf.inputs[0])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    x = -600
    y = -600
    for img in images[2:]:
        tex_extra = nodes.new("ShaderNodeTexImage"); tex_extra.image = img; tex_extra.location = (x, y)
        y = y - 300

    return mat