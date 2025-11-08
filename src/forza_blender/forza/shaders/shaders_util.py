from pathlib import Path
import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.pvs.read_pvs import PVSTexture
from forza_blender.forza.textures.texture_util import get_image_from_index

class TextureNodeWrapper:
    def __init__(self, nodes: list[bpy.types.ShaderNodeTexImage], in_uv: bpy.types.NodeSocket, out_rgb: bpy.types.NodeSocket, out_a: bpy.types.NodeSocket):
        self.nodes = nodes
        self.in_uv = in_uv
        self.out_rgb = out_rgb
        self.out_a = out_a

def generate_image_texture_nodes_for_material(forza_mesh: ForzaMesh, track_folder_path, nodes, links, material_index: int):
    texture_indexes = forza_mesh.track_bin.material_sets[0].materials[material_index].texture_sampler_indices
    textures: list[TextureNodeWrapper] = [None] * len(texture_indexes)

    for i, texture_index in enumerate(texture_indexes):
        if texture_index == -2:
            continue
        if texture_index == -1:
            textures[i] = generate_inherited_texture_nodes(forza_mesh, track_folder_path, nodes, links, i)
            continue

        pvs_texture, texture_file_index, is_stx = forza_mesh.textures[texture_index]

        # get texture
        loaded_texture_image = None

        texture_img = get_image_from_index(track_folder_path, texture_file_index)
        if texture_img is not None:
            loaded_texture_image = texture_img
        else:
            addon_dir = Path(__file__).resolve().parent
            img_path = addon_dir / r"null.png"
            loaded_texture_image = bpy.data.images.load(str(img_path), check_existing=True)

        # create image texture node
        texture_node = nodes.new("ShaderNodeTexImage")
        texture_node.label = F"t{i}"
        texture_node.image = loaded_texture_image
        texture_node.image.alpha_mode = "CHANNEL_PACKED"

        # if the image is from .stx.bin, create UV mapping node
        if is_stx and pvs_texture.u_scale != 1.0 and pvs_texture.v_scale != 1.0 and pvs_texture.u_translate != 0.0 and pvs_texture.v_translate != 0.0:
            uv_node = nodes.new("ShaderNodeVectorMath")
            uv_node.operation = "MULTIPLY_ADD"
            uv_node.inputs["Vector_001"].default_value = (pvs_texture.u_scale, pvs_texture.v_scale, 0)
            uv_node.inputs["Vector_002"].default_value = (pvs_texture.u_translate, -(pvs_texture.v_scale + pvs_texture.v_translate), 0)
            links.new(uv_node.outputs["Vector"], texture_node.inputs["Vector"])
            in_uv = uv_node.inputs["Vector"]
        else:
            in_uv = texture_node.inputs["Vector"]

        textures[i] = TextureNodeWrapper([texture_node], in_uv, texture_node.outputs["Color"], texture_node.outputs["Alpha"])

    return textures

def generate_inherited_texture_nodes(forza_mesh: ForzaMesh, track_folder_path, nodes, links, index: int):
    texture_attribute = nodes.new("ShaderNodeAttribute")
    texture_attribute.attribute_type = "INSTANCER"
    texture_attribute.attribute_name = "texture"

    uv_scale_attribute = nodes.new("ShaderNodeAttribute")
    uv_scale_attribute.attribute_type = "INSTANCER"
    uv_scale_attribute.attribute_name = "uv_scale"

    uv_translate_attribute = nodes.new("ShaderNodeAttribute")
    uv_translate_attribute.attribute_type = "INSTANCER"
    uv_translate_attribute.attribute_name = "uv_translate"

    uv_node = nodes.new("ShaderNodeVectorMath")
    uv_node.operation = "MULTIPLY_ADD"
    links.new(uv_scale_attribute.outputs["Vector"], uv_node.inputs["Vector_001"])
    links.new(uv_translate_attribute.outputs["Vector"], uv_node.inputs["Vector_002"])

    texture_nodes = [None] * len(forza_mesh.inherited_textures)

    prev_mix_node = None
    for i, texture_file_index in enumerate(forza_mesh.inherited_textures):
        compare_node = nodes.new("ShaderNodeMath")
        compare_node.operation = "LESS_THAN"
        compare_node.inputs["Value_001"].default_value = i
        links.new(texture_attribute.outputs["Fac"], compare_node.inputs["Value"])

        # get texture
        loaded_texture_image = None

        texture_img = get_image_from_index(track_folder_path, texture_file_index)
        if texture_img is not None:
            loaded_texture_image = texture_img
        else:
            addon_dir = Path(__file__).resolve().parent
            img_path = addon_dir / r"null.png"
            loaded_texture_image = bpy.data.images.load(str(img_path), check_existing=True)

        # create image texture node
        texture_node = nodes.new("ShaderNodeTexImage")
        texture_node.label = F"t{index}_{i}"
        texture_node.image = loaded_texture_image
        texture_node.image.alpha_mode = "CHANNEL_PACKED"
        links.new(uv_node.outputs["Vector"], texture_node.inputs["Vector"])

        mix_node = nodes.new("ShaderNodeMix")
        mix_node.data_type = "VECTOR"
        links.new(compare_node.outputs["Value"], mix_node.inputs["Factor"])
        links.new(texture_node.outputs["Color"], mix_node.inputs["A"])

        texture_nodes[i] = texture_node

        if prev_mix_node is not None:
            links.new(prev_mix_node.outputs["Result"], mix_node.inputs["B"])
        prev_mix_node = mix_node

    return TextureNodeWrapper(texture_nodes, uv_node.inputs["Vector"], prev_mix_node.outputs["Result"], None)

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