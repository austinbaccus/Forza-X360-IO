from pathlib import Path
import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.textures.texture_util import get_image_from_index

def add_extra_images_to_material(mat, images, start_idx, create_empty_nodes: bool):
    x = -600
    y = -300
    for img in images[start_idx:]:
        if img is not None or create_empty_nodes:
            tex_extra = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex_extra.image = img; tex_extra.location = (x, y)
            y = y - 300

def get_images_from_mesh(forza_mesh: ForzaMesh, path_last_texture_folder):
    images = []
    for texture in forza_mesh.textures:
        texture_img = get_image_from_index(path_last_texture_folder, texture.texture_file_name)
        if texture_img is not None:
            images.append(texture_img)
        else:
            # append NULL texture
            addon_dir = Path(__file__).resolve().parent
            img_path = addon_dir / r"null.png"
            images.append(bpy.data.images.load(str(img_path), check_existing=True))

    return images

def generate_image_texture_nodes_for_material(forza_mesh: ForzaMesh, path_last_texture_folder, nodes, links):
    x = 0
    y = 0
    i = 0
    for texture in forza_mesh.textures:
        # get texture
        loaded_texture_image = None

        texture_img = get_image_from_index(path_last_texture_folder, texture.texture_file_name)
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
    for j in range(len(forza_mesh.textures)):
        # if scale is not (1,1), create texture coordinate node and mapping node
        if forza_mesh.textures[j].u_scale != 1.0 or forza_mesh.textures[j].v_scale != 1.0:
            map_node = nodes.new('ShaderNodeMapping')
            map_node.inputs['Scale'].default_value = (forza_mesh.textures[j].u_scale, forza_mesh.textures[j].v_scale, 1.0)
            map_node.location = (x-300, y)
            tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
            tex_coord_node.location = (x-600, y)
            links.new(tex_coord_node.outputs[2], map_node.inputs["Vector"])
            links.new(map_node.outputs[0], nodes[j].inputs["Vector"])
        y = y - 300
