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
            # TODO: inherit texture from the current model instance
            is_stx = False
            texture_file_index = 0xFFFFFFFF
            pvs_texture = PVSTexture(0xFFFFFFFF, -1, 1, 1, 0, 0)
        else:
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