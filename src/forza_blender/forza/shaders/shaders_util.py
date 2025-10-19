from pathlib import Path
import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.textures.texture_util import get_image_from_index

def generate_image_texture_nodes_for_material(forza_mesh: ForzaMesh, track_folder_path, nodes, links, material_index: int):
    x = 0
    y = 0
    i = 0
    for texture_sampler_index in forza_mesh.track_bin.material_sets[0].materials[material_index].texture_sampler_indices:
        if texture_sampler_index == -2:
            continue
        if texture_sampler_index == -1:
            # TODO: inherit texture from the current model instance
            texture = forza_mesh.textures[0]
        else:
            texture = forza_mesh.textures[texture_sampler_index]

        # get texture
        loaded_texture_image = None

        texture_img = get_image_from_index(track_folder_path, texture.texture_file_name)
        if texture_img is not None:
            loaded_texture_image = texture_img
        else:
            addon_dir = Path(__file__).resolve().parent
            img_path = addon_dir / r"null.png"
            loaded_texture_image = bpy.data.images.load(str(img_path), check_existing=True)

        # create image texture node
        texture_node = nodes.new("ShaderNodeTexImage")
        texture_node.image = loaded_texture_image
        texture_node.image.alpha_mode = 'NONE'
        texture_node.location = (x, y)
        y = y - 300
        i = i + 1

    y = 0
    j = 0
    for texture_sampler_index in forza_mesh.track_bin.material_sets[0].materials[material_index].texture_sampler_indices:
        if texture_sampler_index == -2:
            continue
        if texture_sampler_index == -1:
            texture = forza_mesh.textures[0]
        else:
            texture = forza_mesh.textures[texture_sampler_index]

        # if scale is not (1,1), create texture coordinate node and mapping node
        if texture.u_scale != 1.0 or texture.v_scale != 1.0:
            map_node = nodes.new('ShaderNodeMapping')
            map_node.inputs['Scale'].default_value = (texture.u_scale, texture.v_scale, 1.0)
            map_node.location = (x-300, y)
            tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
            tex_coord_node.location = (x-600, y)
            links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
            links.new(map_node.outputs[0], nodes[j].inputs["Vector"])
        y = y - 300
        j += 1

def attach_uv_map_node(mat, x, y, uvmap, target_node_idx):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    uv_map_node = nodes.new('ShaderNodeUVMap'); uv_map_node.uv_map = uvmap; uv_map_node.location = (x, y)
    links.new(uv_map_node.outputs[0], nodes[target_node_idx].inputs[0])

def attach_darken_node(mat, x, y, diffuse_node, shadow_node, output_node = None, output_idx_input_idx = 0):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (x, y); mix_darken_node.blend_type = 'DARKEN'
    links.new(diffuse_node.outputs[0], mix_darken_node.inputs[1])
    links.new(shadow_node.outputs[0], mix_darken_node.inputs[2])
    links.new(mix_darken_node.inputs[2], mix_darken_node.inputs[2])
    if output_node is not None: links.new(mix_darken_node.outputs[0], output_node.inputs[output_idx_input_idx])

def attach_mix_node(mat, x, y, diffuse_node, shadow_node, output_node = None, output_idx_input_idx = 0):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    mix_darken_node = nodes.new(type='ShaderNodeMixRGB'); mix_darken_node.location = (x, y); mix_darken_node.blend_type = 'MIX'
    links.new(diffuse_node.outputs[0], mix_darken_node.inputs[1])
    links.new(shadow_node.outputs[0], mix_darken_node.inputs[2])
    links.new(mix_darken_node.inputs[2], mix_darken_node.inputs[2])
    if output_node is not None: links.new(mix_darken_node.outputs[0], output_node.inputs[output_idx_input_idx])