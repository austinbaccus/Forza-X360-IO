from pathlib import Path
import re
import bpy # type: ignore
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
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    return mat

def _generate_image_from_bix_texture_path(path: Path):
    if path.is_file():
        img = Bix.get_image_from_bix(path.resolve())
        return img
    return None

def _get_pvstexture_path(pvs_texture: PVSTexture, path_root: Path):
    hex_str = f"_0x{pvs_texture.texture_file_name:08x}.bix"
    full_texture_path = path_root / Path(hex_str)
    return full_texture_path