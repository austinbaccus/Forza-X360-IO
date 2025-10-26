from pathlib import Path
import bpy # type: ignore
import tempfile
import struct
import os
import numpy as np
from ..utils.deswizzle import Deswizzler

class Bix():
    def get_image_from_bix(filepath, save_image: bool = False):
        # note: each texture (in FM3 at least) is comprised of two files. 
        # the second file ends with "_B". this file contains the actual pixels I think.
        path = Path(filepath)
        directory = path.parent
        filename = path.stem
        filetype = path.suffix 

        if filename.endswith("_B"):
            raise ValueError("Don't load the `_B` version fo a texture file.")

        # get image a and b names
        file_a_name: str = filename + filetype
        file_b_name: str = filename + "_B" + filetype

        # image a and b paths
        file_a_path: str = directory / file_a_name
        file_b_path: str = directory / file_b_name

        width: int = None
        height: int = None
        levels: int = None
        format: int = None
        total_size: int = None
        main_size: int = None

        # read file `a` (Big Endian format)
        with open(file_a_path, "rb") as f:
            num = int.from_bytes(f.read(4), byteorder="big", signed=False)
            if num != 1112102960 and num != 1112102961:
                raise TypeError("Unrecognized bix file format. " + str(num))

            width = int.from_bytes(f.read(4), byteorder="big", signed=False)
            height = int.from_bytes(f.read(4), byteorder="big", signed=False)
            levels = int.from_bytes(f.read(4), byteorder="big", signed=False)
            format = int.from_bytes(f.read(4), byteorder="big", signed=False)
            total_size = int.from_bytes(f.read(4), byteorder="big", signed=False)
            main_size = int.from_bytes(f.read(4), byteorder="big", signed=False)

        # read file `b`
        dumped_image_data = np.fromfile(file_b_path, np.uint8)

        if format == 438305108: # D3DFMT_DXT5
            dumped_image_data = Bix.flip_byte_order_16bit(dumped_image_data)
            blocks = Deswizzler.XGUntileSurfaceToLinearTexture(dumped_image_data, width, height, "DXT5")
            dds = Bix.wrap_as_dds_dx5_bc3_linear(blocks.tobytes(), width, height)
        elif format == 438305106: # D3DFMT_DXT1
            dumped_image_data = Bix.flip_byte_order_16bit(dumped_image_data)
            blocks = Deswizzler.XGUntileSurfaceToLinearTexture(dumped_image_data, width, height, "DXT1")
            dds = Bix.wrap_as_dds_dx10_bc(71, blocks.tobytes(), width, height) # DXGI_FORMAT_BC1_UNORM
        elif format == 438305147: # D3DFMT_DXT5A
            dumped_image_data = Bix.flip_byte_order_16bit(dumped_image_data)
            blocks = Deswizzler.XGUntileSurfaceToLinearTexture(dumped_image_data, width, height, "DXT1")
            dds = Bix.wrap_as_dds_dx10_bc(80, blocks.tobytes(), width, height) # DXGI_FORMAT_BC4_UNORM
        elif format == 438305137: # D3DFMT_DXN
            dumped_image_data = Bix.flip_byte_order_16bit(dumped_image_data)
            blocks = Deswizzler.XGUntileSurfaceToLinearTexture(dumped_image_data, width, height, "DXT5")
            dds = Bix.wrap_as_dds_dx10_bc(83, blocks.tobytes(), width, height) # DXGI_FORMAT_BC5_UNORM
        else:
            return None
            #raise ValueError("Unsupported deswizzling format!")

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

    def wrap_as_dds_dx10_bc(fmt_dxgi: int, blocks_linear: bytes, width: int, height: int) -> bytes:
        # DXGI_FORMAT values: BC1=71, BC2=74, BC3=77, BC4U=80, BC5U=83, BC6H_UF16=95, BC7=98
        DDS_MAGIC = b'DDS '
        DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PIXELFORMAT, DDSD_LINEARSIZE = 0x1, 0x2, 0x4, 0x1000, 0x80000
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
        header = struct.pack('<I I I I I I I 11I',
            124, flags, height, width, len(blocks_linear), 0, 1, *([0]*11)
        )
        # FourCC 'DX10'
        pixelfmt = struct.pack('<I I 4s I I I I I', 32, 0x4, b'DX10', 0, 0, 0, 0, 0)
        caps = struct.pack('<I I I I', 0x1000, 0, 0, 0)  # DDSCAPS_TEXTURE
        reserved2 = b'\x00\x00\x00\x00'
        # DDS_HEADER_DXT10
        # resourceDimension=3 (TEXTURE2D), arraySize=1
        dxt10 = struct.pack('<I I I I I', fmt_dxgi, 3, 0, 1, 0)
        return DDS_MAGIC + header + pixelfmt + caps + reserved2 + dxt10 + blocks_linear

    def wrap_as_dds_dx5_bc3_linear(blocks_linear: bytes, width: int, height: int) -> bytes:
        DDS_MAGIC = b'DDS '
        DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PIXELFORMAT, DDSD_LINEARSIZE = 0x1, 0x2, 0x4, 0x1000, 0x80000
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE

        header = struct.pack('<I I I I I I I 11I',
            124, flags, height, width, len(blocks_linear), 0, 1, *([0]*11)
        )
        DDPF_FOURCC = 0x4
        pixelfmt = struct.pack('<I I 4s I I I I I', 32, DDPF_FOURCC, b'DXT5', 0, 0, 0, 0, 0)
        caps = struct.pack('<I I I I', 0x1000, 0, 0, 0)  # DDSCAPS_TEXTURE
        reserved2 = b'\x00\x00\x00\x00'
        return DDS_MAGIC + header + pixelfmt + caps + reserved2 + blocks_linear
    
    def wrap_as_dds_dx10_bc7(blocks_linear: bytes, width: int, height: int) -> bytes:
        DDS_MAGIC = b'DDS '
        DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PIXELFORMAT, DDSD_LINEARSIZE = 0x1, 0x2, 0x4, 0x1000, 0x80000
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE

        # Standard DDS header (no mipmaps)
        header = struct.pack('<I I I I I I I 11I',
            124, flags, height, width, len(blocks_linear), 0, 1, *([0]*11)
        )

        # Pixel format = 'DX10' extension
        pixelfmt = struct.pack('<I I 4s I I I I I', 32, 0x4, b'DX10', 0, 0, 0, 0, 0)

        # Caps
        caps = struct.pack('<I I I I', 0x1000, 0, 0, 0)  # DDSCAPS_TEXTURE
        reserved2 = b'\x00\x00\x00\x00'

        # DDS_HEADER_DXT10: DXGI_FORMAT_BC7_UNORM = 98, TEXTURE2D=3, arraySize=1
        dxt10 = struct.pack('<I I I I I', 98, 3, 0, 1, 0)

        return DDS_MAGIC + header + pixelfmt + caps + reserved2 + dxt10 + blocks_linear

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
