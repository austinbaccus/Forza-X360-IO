from pathlib import Path
import os
import re
import bpy # type: ignore

def convert_texture_name_to_decimal(name: str) -> int:
    m = re.search(r'(-?)0x([0-9A-Fa-f_]+)', name)
    if not m:
        raise ValueError("No hex literal like 0x... found")
    sign = -1 if m.group(1) == '-' else 1
    digits = m.group(2).replace('_', '')
    return sign * int(digits, 16)

def get_image_from_index(root: Path, image_index: str, filetype: str = "dds") -> bpy.types.Image:
    # all texture filenames are integers written in hexadecimal. this also doubles as an index.
    # shaders and models reference textures by this index (in decimal format).
    # this method looks for the image file with a matching hexadecimal string filename as the `index` parameter and returns it as an image.

    hex_str = f"_0x{int(image_index):08X}.{filetype}"
    full_texture_path = root / Path("bin\\textures") / Path(hex_str)
    full_texture_path_str = str(full_texture_path.resolve())

    if not os.path.exists(full_texture_path_str):
        # try bin
        hex_str = f"_0x{int(image_index):08X}.bin"
        full_texture_path = root / Path("bin") / Path(hex_str)
        full_texture_path_str = str(full_texture_path.resolve())
        
        if not os.path.exists(full_texture_path_str):
            print (f"Image not found: {full_texture_path.stem}")
            return None
        
        return None # TODO: load .bin texture images (once they're implemented)
    img = bpy.data.images.load(full_texture_path_str, check_existing=True)
    return img