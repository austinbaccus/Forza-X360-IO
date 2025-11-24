import numpy as np

class Deswizzler:
    def get_block_info(d3d_format: int):
        gpu_format = d3d_format & 0x3F
        match gpu_format:
            case 2: # 8
                return 1, 1
            case 6: # 8_8_8_8
                return 1, 4
            case 18 | 59: # DXT1, DXT5A
                return 4, 8
            case 19 | 20 | 49: # DXT3, DXT5, DXN
                return 4, 16
            case _:
                raise RuntimeError("Unsupported GPU format.")

    def calc_texture_size(d3d_format: int, width_texels: int, height_texels: int):
        block_size, texel_pitch = Deswizzler.get_block_info(d3d_format)

        width_in_blocks = (width_texels + block_size - 1) // block_size
        height_in_blocks = (height_texels + block_size - 1) // block_size

        tiled = (d3d_format & 0x100) >> 8
        if tiled:
            width_alignment = 32
        else:
            width_alignment = max(256 // texel_pitch, 32)
        aligned_width = (width_in_blocks + width_alignment - 1) & ~(width_alignment - 1)
        aligned_height = (height_in_blocks + 31) & ~31
        size = aligned_width * aligned_height * texel_pitch
        return (size + 4095) & ~4095

    def XGUntileSurfaceToLinearTexture(data: np.ndarray, width: int, height: int, d3d_format: int, levels: int):
        block_size, texel_pitch = Deswizzler.get_block_info(d3d_format)

        offset_x = 0
        offset_y = 0
        if levels != 1 and (width <= 16 or height <= 16):
            if width <= height:
                offset_x = 16 // block_size
            else:
                offset_y = 16 // block_size

        width_in_blocks = (width + block_size - 1) // block_size
        height_in_blocks = (height + block_size - 1) // block_size

        x, y = np.meshgrid(np.arange(offset_x, offset_x + width_in_blocks), np.arange(offset_y, offset_y + height_in_blocks))

        tiled = (d3d_format & 0x100) >> 8
        if tiled:
            src_offset = Deswizzler.XGAddress2DTiledOffset(x, y, width_in_blocks, texel_pitch)
            data = data.reshape((-1, texel_pitch))
            return data[src_offset]
        else:
            width_alignment = max(256 // texel_pitch, 32)
            aligned_width = (width_in_blocks + width_alignment - 1) & ~(width_alignment - 1)
            data = data.reshape((-1, aligned_width, texel_pitch))
            return data[y, x]

    # from xgraphics.h from Xbox 360 XDK
    def XGAddress2DTiledOffset(x, y, Width, TexelPitch):
        AlignedWidth = (Width + 31) & ~31
        LogBpp = (TexelPitch >> 2) + ((TexelPitch >> 1) >> (TexelPitch >> 2))
        Macro = ((x >> 5) + (y >> 5) * (AlignedWidth >> 5)) << (LogBpp + 7)
        Micro = (((x & 7) + ((y & 6) << 2)) << LogBpp)
        Offset = Macro + ((Micro & ~15) << 1) + (Micro & 15) + ((y & 8) << (3 + LogBpp)) + ((y & 1) << 4)

        return (((Offset & ~511) << 3) + ((Offset & 448) << 2) + (Offset & 63) + ((y & 16) << 7) + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6)) >> LogBpp
