from pathlib import Path
import bpy # type: ignore
import tempfile
import struct
import os
import numpy as np
from ..utils.deswizzle import Deswizzler

class Bix():
    def wrap_as_dds(data: bytes, d3d_format: int, width: int, height: int, mip_0_size: int) -> bytes:
        # Blender supports only DXT1, DXT3 and DXT5
        d3d_to_fourcc = {
            438305106: b"DXT1", # D3DFMT_DXT1
            438337362: b"DXT1", # MAKESRGBFMT(D3DFMT_DXT1)
            438337363: b"DXT3", # MAKESRGBFMT(D3DFMT_DXT3)
            438305108: b"DXT5", # D3DFMT_DXT5
            438337364: b"DXT5", # MAKESRGBFMT(D3DFMT_DXT5)
        }
        d3d_to_dxgi = {
            # # DXGI_FORMAT_BC1_UNORM
            # 438305106: 71, # D3DFMT_DXT1
            # 438337362: 71, # MAKESRGBFMT(D3DFMT_DXT1)
            # # DXGI_FORMAT_BC2_UNORM
            # 438337363: 74, # MAKESRGBFMT(D3DFMT_DXT3)
            # # DXGI_FORMAT_BC3_UNORM
            # 438305108: 77, # D3DFMT_DXT5
            # 438337364: 77, # MAKESRGBFMT(D3DFMT_DXT5)
            # DXGI_FORMAT_BC4_UNORM
            438305147: 80, # D3DFMT_DXT5A
            438337403: 80, # MAKESRGBFMT(D3DFMT_DXT5A)
            # DXGI_FORMAT_BC5_UNORM
            438305137: 83, # D3DFMT_DXN
            438337393: 83, # MAKESRGBFMT(D3DFMT_DXN)
            # DXGI_FORMAT_B8G8R8A8_UNORM
            405275014: 87, # D3DFMT_A8R8G8B8
            # DXGI_FORMAT_B8G8R8X8_UNORM
            673710470: 88, # D3DFMT_X8R8G8B8
            673742726: 88, # MAKESRGBFMT(D3DFMT_X8R8G8B8)
            673742470: 88, # D3DFMT_LIN_X8R8G8B8
            # DXGI_FORMAT_R8_UNORM
            671088898: 61, # D3DFMT_L8
        }
        is_dxt10 = d3d_format not in d3d_to_fourcc
        if is_dxt10 and d3d_format not in d3d_to_dxgi:
            print("Unsupported D3D format:", d3d_format)
            return None

        DDS_MAGIC = b"DDS "
        DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PIXELFORMAT, DDSD_LINEARSIZE = 0x1, 0x2, 0x4, 0x1000, 0x80000
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
        header = struct.pack("<I I I I I I I 44x",
            124, flags, height, width, mip_0_size, 1, 1
        )

        DDPF_FOURCC = 0x4
        fourcc = b"DX10" if is_dxt10 else d3d_to_fourcc[d3d_format]
        pixelfmt = struct.pack("<I I 4s I I I I I", 32, DDPF_FOURCC, fourcc, 0, 0, 0, 0, 0)

        DDSCAPS_TEXTURE = 0x1000
        caps = DDSCAPS_TEXTURE
        header2 = struct.pack("<I I I I 4x", caps, 0, 0, 0)

        result = DDS_MAGIC + header + pixelfmt + header2
        if is_dxt10:
            # DDS_HEADER_DXT10
            # resourceDimension=3 (TEXTURE2D), arraySize=1
            dxgi_format = d3d_to_dxgi[d3d_format]
            dxt10 = struct.pack("<I I I I I", dxgi_format, 3, 0, 1, 0)
            result += dxt10
        return result + data

    def texture_to_dds(data: np.ndarray, d3d_format: int, width: int, height: int, levels: int):
        endian = (d3d_format & 0xC0) >> 6
        if endian == 1: # GPUENDIAN_8IN16
            data = Bix.flip_byte_order_16bit(data)
        elif endian == 2: # GPUENDIAN_8IN32
            data = Bix.flip_byte_order_32bit(data)
        elif endian != 0: # GPUENDIAN_NONE
            raise RuntimeError("Unknown texture format endian")

        blocks = Deswizzler.XGUntileSurfaceToLinearTexture(data, width, height, d3d_format, levels)
        mip_0_size = len(blocks)
        linear_data = blocks.tobytes()
        return Bix.wrap_as_dds(linear_data, d3d_format, width, height, mip_0_size)

    def get_image_from_bix(path: Path, save_image: bool = False):
        # note: each texture (in FM3 at least) is comprised of two files. 
        # The file with the "_B" suffix stores the mip 0. The header and the remaining mips are stored in a separate file.
        directory = path.parent
        filename = path.stem
        filetype = path.suffix 

        if filename.endswith("_B"):
            raise ValueError("Don't load the `_B` version of a texture file.")

        # get file names
        file_chain_name = f"{filename}{filetype}"
        file_base_name = f"{filename}_B{filetype}"

        # file paths
        file_chain_path = directory / file_chain_name
        file_base_path = directory / file_base_name

        # read chain file (Big Endian format)
        with open(file_chain_path, "rb") as f:
            buf = f.read(28)
            num = struct.unpack_from(">I", buf)[0]
            if num != 1112102960 and num != 1112102961:
                raise TypeError("Unrecognized bix file format. " + str(num))

            width = struct.unpack_from(">I", buf, 4)[0]
            height = struct.unpack_from(">I", buf, 8)[0]
            levels = struct.unpack_from(">I", buf, 12)[0]
            d3d_format = struct.unpack_from(">I", buf, 16)[0]
            total_size = struct.unpack_from(">I", buf, 20)[0]
            base_size = struct.unpack_from(">I", buf, 24)[0]

        # read base file
        dumped_image_data = np.fromfile(file_base_path, np.uint8)

        dds = Bix.texture_to_dds(dumped_image_data, d3d_format, width, height, levels)

        if save_image:
            image_filename = "textures/" + filename + ".dds"
            image_filepath = directory / image_filename
            with open(image_filepath.resolve(), 'wb') as f: 
                f.write(dds)
            with open(image_filepath.resolve(), 'r') as f:
                image_filepath_Str = str(image_filepath.resolve())
                img = bpy.data.images.load(image_filepath_Str, check_existing=True)
                img.name = filename
                if hasattr(img, "colorspace_settings"):
                    img.colorspace_settings.name = "sRGB"
                img.pack()
                return img
        else:
            img = None
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".dds")
                tmp.write(dds)
                tmp.flush()
                tmp.close()
                img = bpy.data.images.load(tmp.name, check_existing=False)
                img.name = filename
                if hasattr(img, "colorspace_settings"):
                    img.colorspace_settings.name = "sRGB"
                img.pack()
            finally:
                try:
                    os.remove(tmp.name)
                except Exception:
                    pass
            return img

    def _compact1by1(v: int) -> int:
        v &= 0x55555555
        v = (v | (v >> 1)) & 0x33333333
        v = (v | (v >> 2)) & 0x0F0F0F0F
        v = (v | (v >> 4)) & 0x00FF00FF
        v = (v | (v >> 8)) & 0x0000FFFF
        return v

    def _morton_decode2d(code: int) -> tuple[int, int]:
        x = Bix._compact1by1(code)
        y = Bix._compact1by1(code >> 1)
        return x, y

    def unswizzle_bc_blocks_morton(data: bytes, width: int, height: int, block_bytes: int = 16) -> bytes:
        bw, bh = width // 4, height // 4
        n = bw * bh
        assert len(data) == n * block_bytes, "length mismatch for BCn blocks"
        out = bytearray(len(data))
        for i in range(n):
            x, y = Bix._morton_decode2d(i)
            if x < bw and y < bh:
                dst = (y * bw + x) * block_bytes
                src = i * block_bytes
                out[dst:dst+block_bytes] = data[src:src+block_bytes]
        return bytes(out)


# ..................................


    def xg_address_2d_tiled_x(block_offset, width_in_blocks, texel_byte_pitch):
        aligned_width = (width_in_blocks + 31) & ~31
        log_bpp = (texel_byte_pitch >> 2) + (
            (texel_byte_pitch >> 1) >> (texel_byte_pitch >> 2)
        )
        offset_byte = block_offset << log_bpp
        offset_tile = (
            ((offset_byte & ~0xFFF) >> 3)
            + ((offset_byte & 0x700) >> 2)
            + (offset_byte & 0x3F)
        )
        offset_macro = offset_tile >> (7 + log_bpp)

        macro_x = (offset_macro % (aligned_width >> 5)) << 2
        tile = (((offset_tile >> (5 + log_bpp)) & 2) + (offset_byte >> 6)) & 3
        macro = (macro_x + tile) << 3
        micro = (
            (((offset_tile >> 1) & ~0xF) + (offset_tile & 0xF))
            & ((texel_byte_pitch << 3) - 1)
        ) >> log_bpp

        return macro + micro

    def xg_address_2d_tiled_y(block_offset, width_in_blocks, texel_byte_pitch):
        aligned_width = (width_in_blocks + 31) & ~31
        log_bpp = (texel_byte_pitch >> 2) + (
            (texel_byte_pitch >> 1) >> (texel_byte_pitch >> 2)
        )
        offset_byte = block_offset << log_bpp
        offset_tile = (
            ((offset_byte & ~0xFFF) >> 3)
            + ((offset_byte & 0x700) >> 2)
            + (offset_byte & 0x3F)
        )
        offset_macro = offset_tile >> (7 + log_bpp)

        macro_y = (offset_macro // (aligned_width >> 5)) << 2
        tile = ((offset_tile >> (6 + log_bpp)) & 1) + ((offset_byte & 0x800) >> 10)
        macro = (macro_y + tile) << 3
        micro = (
            (
                (offset_tile & ((texel_byte_pitch << 6) - 1 & ~0x1F))
                + ((offset_tile & 0xF) << 1)
            )
            >> (3 + log_bpp)
        ) & ~1

        return macro + micro + ((offset_tile & 0x10) >> 4)

    def xbox_360_convert_to_linear_texture(data, pixel_width, pixel_height):
        dest_data = bytearray(len(data))
        block_pixel_size = 4
        texel_byte_pitch = 8

        width_in_blocks = pixel_width // block_pixel_size
        height_in_blocks = pixel_height // block_pixel_size

        for j in range(height_in_blocks):
            for i in range(width_in_blocks):
                block_offset = j * width_in_blocks + i
                x = Bix.xg_address_2d_tiled_x(block_offset, width_in_blocks, texel_byte_pitch)
                y = Bix.xg_address_2d_tiled_y(block_offset, width_in_blocks, texel_byte_pitch)
                src_byte_offset = (
                    j * width_in_blocks * texel_byte_pitch + i * texel_byte_pitch
                )
                dest_byte_offset = (
                    y * width_in_blocks * texel_byte_pitch + x * texel_byte_pitch
                )

                if dest_byte_offset + texel_byte_pitch > len(dest_data):
                    continue
                dest_data[dest_byte_offset : dest_byte_offset + texel_byte_pitch] = data[
                    src_byte_offset : src_byte_offset + texel_byte_pitch
                ]

        return dest_data

    def flip_byte_order_16bit(data: np.ndarray):
        if data.size % 2 != 0:
            raise ValueError(
                "Data length must be a multiple of 2 bytes for 16-bit flipping."
            )

        return data.view(np.uint16).byteswap().view(np.uint8)
    
    def flip_byte_order_32bit(data: np.ndarray):
        if data.size % 4 != 0:
            raise ValueError(
                "Data length must be a multiple of 4 bytes for 32-bit flipping."
            )

        return data.view(np.uint32).byteswap().view(np.uint8)
