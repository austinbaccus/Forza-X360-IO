import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.shaders.shaders_util import *
from forza_blender.forza.textures.texture_util import get_image_from_index

def generate_blender_materials_for_mesh(forza_mesh: ForzaMesh, forza_last_texture_folder):
    materials = []
    for shader_filename in forza_mesh.shader_filenames:
        shader_filename_simple = (shader_filename.split('\\')[-1]).split('.')[0]
        if "diff_spec_1" == shader_filename_simple:
            materials.append(_diff_spec_1(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_opac_2" == shader_filename_simple:
            materials.append(_diff_opac_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_spec_opac_refl_3" == shader_filename_simple:
            materials.append(_diff_spec_opac_refl_3(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_spec_refl" == shader_filename_simple:
            materials.append(_diff_spec_refl(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_spec_refl_3" == shader_filename_simple:
            materials.append(_diff_spec_refl_3(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "road_blnd_2" == shader_filename_simple:
            materials.append(_road_blnd_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "road_diff_spec_ovly_blur_detailscale_2" == shader_filename_simple:
            materials.append(_road_diff_spec_ovly_blur_detailscale_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "ocean_anim_norm_refl_5" == shader_filename_simple:
            materials.append(_ocean_anim_norm_refl_5(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "bush_diff_opac_2_2sd" == shader_filename_simple:
            materials.append(_bush_diff_opac_2_2sd(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "tree_diff_opac_2_2sd" == shader_filename_simple:
            materials.append(_tree_diff_opac_2_2sd(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        elif "diff_opac_clampv_2" == shader_filename_simple:
            materials.append(_diff_opac_clampv_2(forza_mesh, forza_last_texture_folder, shader_filename_simple))
        else:
            materials.append(_unknown(forza_mesh, forza_last_texture_folder, shader_filename_simple))
    return materials

def _unknown(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage"); tex.image = images[0]; tex.location = (-600, 0)
        if tex.image is not None:
            tex.image.alpha_mode = 'NONE'
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 1, False)

    return mat

# buildings
def _diff_opac_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

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

    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 1, False)

    return mat

def _diff_spec_1(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        diffuse_node = nodes.new("ShaderNodeTexImage"); diffuse_node.image = images[0]; diffuse_node.location = (-600, 0)
        if diffuse_node.image is not None:
            diffuse_node.image.alpha_mode = 'NONE'
        ambient_occlusion_node = nodes.new("ShaderNodeTexImage"); ambient_occlusion_node.image = images[1]; ambient_occlusion_node.location = (-600, -300)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (-300, 150); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "UVMap2"; uv_map_node.location = (-900, -300)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (0, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (300, 0)

        # link
        links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    
    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 2, False)

    return mat

def _diff_spec_refl(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    return _diff_spec_opac_refl_3(forza_mesh, path_last_texture_folder, shader_name)

def _diff_spec_refl_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        unk1 = nodes.new("ShaderNodeTexImage"); unk1.image = images[0]; unk1.location = (-600, 600); 
        unk2 = nodes.new("ShaderNodeTexImage"); unk2.image = images[0]; unk2.location = (-600, 300); 
        diffuse_node = nodes.new("ShaderNodeTexImage"); diffuse_node.image = images[2]; diffuse_node.location = (-600, 0)
        if diffuse_node.image is not None:
            diffuse_node.image.alpha_mode = 'NONE'
        ambient_occlusion_node = nodes.new("ShaderNodeTexImage"); ambient_occlusion_node.image = images[3]; ambient_occlusion_node.location = (-600, -300)
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (-300, 150); mix_rgb_node.blend_type = 'DARKEN'
        uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = "UVMap2"; uv_map_node.location = (-900, -300)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (0, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (300, 0)

        # link
        links.new(uv_map_node.outputs["UV"], ambient_occlusion_node.inputs["Vector"])
        links.new(mix_rgb_node.outputs[0], bsdf.inputs["Base Color"])
        links.new(diffuse_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(ambient_occlusion_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    
    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 4, False)

    return mat

def _diff_spec_opac_refl_3(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        unk1 = nodes.new("ShaderNodeTexImage"); unk1.image = images[0]; unk1.location = (-600, 600); 
        unk2 = nodes.new("ShaderNodeTexImage"); unk2.image = images[0]; unk2.location = (-600, 300); 
        tex = nodes.new("ShaderNodeTexImage"); tex.image = images[2]; tex.location = (-600, 0); 
        if tex.image is not None:
            tex.image.alpha_mode = 'NONE'
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 3, False)

    return mat

# ocean
def _ocean_anim_norm_refl_5(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        sea_texture_path = r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\AmalfiGP\bin\textures\sea.png"
        bpy.data.images.load(sea_texture_path, check_existing=True)
        tex = nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(sea_texture_path, check_existing=True); tex.location = (-600, 0)
        normal = nodes.new("ShaderNodeTexImage"); normal.image = images[1]; normal.location = (-600, 0)
        normal_map = nodes.new(type='ShaderNodeNormalMap')

        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0)
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(normal.outputs["Color"], normal_map.inputs[0])
        links.new(normal_map.outputs[0], bsdf.inputs["Normal"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    
    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 1, False)

    return mat

# road
def _road_blnd_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    return _road_diff_spec_ovly_blur_detailscale_2(forza_mesh, path_last_texture_folder, shader_name)

def _road_diff_spec_ovly_blur_detailscale_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()

        diffuse1_node = nodes.new("ShaderNodeTexImage"); diffuse1_node.image = images[0]; diffuse1_node.location = (-600, 0); diffuse1_node.image.alpha_mode = 'NONE'
        diffuse2_node = nodes.new("ShaderNodeTexImage"); diffuse2_node.image = images[1]; diffuse2_node.location = (-600, -300); diffuse2_node.image.alpha_mode = 'NONE'
        mix_rgb_node = nodes.new(type='ShaderNodeMixRGB'); mix_rgb_node.location = (-300, 150)
        map_node = nodes.new('ShaderNodeMapping'); map_node.inputs['Scale'].default_value = (4.0, 16.0, 1.0); map_node.location = (-900, -300)
        tex_coord_node = nodes.new(type='ShaderNodeTexCoord')

        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (0, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (300, 0)

        # link
        links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
        links.new(map_node.outputs[0], diffuse1_node.inputs["Vector"])
        links.new(diffuse1_node.outputs["Color"], mix_rgb_node.inputs[1])
        links.new(diffuse2_node.outputs["Color"], mix_rgb_node.inputs[2])
        links.new(mix_rgb_node.outputs[0], bsdf.inputs[0])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    
    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 2, False)

    return mat

# vegetation
def _bush_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage"); tex.image = images[0]; tex.location = (-600, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    
    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 1, False)

    return mat

def _tree_diff_opac_2_2sd(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    return _bush_diff_opac_2_2sd(forza_mesh, path_last_texture_folder, shader_name)

# terrain
def _diff_opac_clampv_2(forza_mesh: ForzaMesh, path_last_texture_folder, shader_name: str):
    images = get_images_from_mesh(forza_mesh, path_last_texture_folder)

    # create material
    mat = bpy.data.materials.new(shader_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links

    # nodes
    if len(images) > 0:
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage"); tex.image = images[0]; tex.location = (-600, 0); tex.image.alpha_mode = 'NONE'
        bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (-200, 0); bsdf.inputs.get("IOR").default_value = 1.02
        out = nodes.new("ShaderNodeOutputMaterial"); out.location = (200, 0)

        # link
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    
    # TODO: is mat passed by reference or value? it won't work if it's passed in by value
    add_extra_images_to_material(mat, images, 1, False)

    return mat