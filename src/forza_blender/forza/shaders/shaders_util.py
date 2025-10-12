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

def create_diffuse_node():
    print()