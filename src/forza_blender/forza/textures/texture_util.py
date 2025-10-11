from pathlib import Path
import os
import re
import bpy # type: ignore
from forza_blender.forza.models.forza_mesh import ForzaMesh
from forza_blender.forza.pvs.read_pvs import PVSTexture
from forza_blender.forza.textures.read_bix import Bix

def convert_texture_name_to_decimal(name: str) -> int:
    m = re.search(r'(-?)0x([0-9A-Fa-f_]+)', name)
    if not m:
        raise ValueError("No hex literal like 0x... found")
    sign = -1 if m.group(1) == '-' else 1
    digits = m.group(2).replace('_', '')
    return sign * int(digits, 16)

def generate_material_from_textures(mat_name, textures: PVSTexture, path_bin: Path):
    images = []
    for texture in textures:
        texture_path = _get_pvstexture_path(texture, path_bin)
        texture_img = _generate_image_from_bix_texture_path(texture_path)
        images.append(texture_img)

    # create material
    mat = bpy.data.materials.new(mat_name)
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

    return mat

def generate_material_from_texture_indices(mat_name, textures: list[PVSTexture], path_bin: Path):
    images = []
    for texture in textures:
        texture_img = get_image_from_index(path_bin, texture.texture_file_name)
        images.append(texture_img)

    # create material
    mat = bpy.data.materials.new(mat_name)
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

def get_image_from_index(root: Path, image_index: str, filetype: str = "dds") -> bpy.types.Image:
    # all texture filenames are integers written in hexadecimal. this also doubles as an index.
    # shaders and models reference textures by this index (in decimal format).
    # this method looks for the image file with a matching hexadecimal string filename as the `index` parameter and returns it as an image.

    hex_str = f"_0x{int(image_index):08X}.{filetype}"
    full_texture_path = root / Path(hex_str)

    full_texture_path_str = str(full_texture_path.resolve())
    if not os.path.exists(full_texture_path_str):
        #raise FileNotFoundError(f"Image not found: {full_texture_path_str}")
        print (f"Image not found: {full_texture_path.stem}")
        return None
    img = bpy.data.images.load(full_texture_path_str, check_existing=True)
    return img

def _generate_image_from_bix_texture_path(path: Path):
    if path.is_file():
        img = Bix.get_image_from_bix(path.resolve())
        return img
    return None

def _get_pvstexture_path(pvs_texture: PVSTexture, path_root: Path):
    hex_str = f"_0x{pvs_texture.texture_file_name:08x}.bix"
    full_texture_path = path_root / Path(hex_str)
    return full_texture_path