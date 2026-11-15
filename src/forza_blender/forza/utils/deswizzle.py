import numpy as np

class Deswizzler:
    def next_multiple(value: int, multiple: int):
        return (value + multiple - 1) & ~(multiple - 1)

    def ceil_div(a: int, b: int):
        return (a + b - 1) // b

    def ceil_log2(value: int):
        return (value - 1).bit_length()

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

    # D3D::GetMipTailBaseLevel()
    def get_tail_level(width: int, height: int):
        return max(0, Deswizzler.ceil_log2(min(width, height)) - 4)

    # D3D::FindTextureSize()
    def get_tiles(d3d_format: int, width: int, height: int, levels: int):
        block_size, texel_pitch = Deswizzler.get_block_info(d3d_format)

        width_pow2 = 1 << Deswizzler.ceil_log2(width)
        height_pow2 = 1 << Deswizzler.ceil_log2(height)

        tiled = (d3d_format & 0x100) >> 8
        if tiled:
            width_alignment = 32
        else:
            width_alignment = max(256 // texel_pitch, 32)

        tail_level = Deswizzler.get_tail_level(width, height)

        tiles = []
        for i in range(min(levels, tail_level + 1)):
            canvas_width = width if i == 0 else width_pow2
            canvas_height = height if i == 0 else height_pow2
            width_in_blocks = Deswizzler.ceil_div(canvas_width, block_size)
            height_in_blocks = Deswizzler.ceil_div(canvas_height, block_size)
            aligned_width = Deswizzler.next_multiple(width_in_blocks, width_alignment)
            aligned_height = Deswizzler.next_multiple(height_in_blocks, 32)
            slice_pitch = aligned_width * aligned_height * texel_pitch
            size = Deswizzler.next_multiple(slice_pitch, 4096)
            tiles.append((width, height, canvas_width, canvas_height, size))
            width >>= 1
            height >>= 1
            width_pow2 >>= 1
            height_pow2 >>= 1
        return tiles

    def get_tiles_base_size(tiles: list):
        size = tiles[0][4]
        return size

    def get_tiles_total_size(tiles: list):
        size = sum(tile_info[4] for tile_info in tiles)
        return size

    # XGRAPHICS::GetMipTailLevelOffsetCoords()
    def get_tail_mips(d3d_format: int, width: int, height: int, canvas_width: int, canvas_height: int, levels: int):
        block_size, _ = Deswizzler.get_block_info(d3d_format)

        log_width = Deswizzler.ceil_log2(canvas_width)
        log_height = Deswizzler.ceil_log2(canvas_height)
        is_x_main_axis = log_width <= log_height
        log_size_max = log_height if is_x_main_axis else log_width

        tail_mips = []
        for level in range(levels):
            offset_x = 0
            offset_y = 0
            if level < 3:
                offset_x = 16 >> level
            else:
                offset_y = 1 << (log_size_max - 1 - (level - 3))
            offset_x //= block_size
            offset_y //= block_size
            if not is_x_main_axis:
                offset_x, offset_y = offset_y, offset_x
            tail_mips.append((width, height, offset_x, offset_y, canvas_width, canvas_height))
            if width > 1:
                width >>= 1
            if height > 1:
                height >>= 1
            if canvas_width > 1:
                canvas_width >>= 1
            if canvas_height > 1:
                canvas_height >>= 1
        return tail_mips

    def get_linear_data(data: np.ndarray, d3d_format: int, width: int, height: int, offset_x: int, offset_y: int, canvas_width: int):
        block_size, texel_pitch = Deswizzler.get_block_info(d3d_format)

        width_in_blocks = Deswizzler.ceil_div(width, block_size)
        height_in_blocks = Deswizzler.ceil_div(height, block_size)

        x, y = np.meshgrid(np.arange(offset_x, offset_x + width_in_blocks), np.arange(offset_y, offset_y + height_in_blocks))

        canvas_width_in_blocks = Deswizzler.ceil_div(canvas_width, block_size)

        tiled = (d3d_format & 0x100) >> 8
        if tiled:
            src_offset = Deswizzler.XGAddress2DTiledOffset(x, y, canvas_width_in_blocks, texel_pitch)
            data = data.reshape((-1, texel_pitch))
            data = data[src_offset]
        else:
            width_alignment = max(256 // texel_pitch, 32)
            aligned_width = Deswizzler.next_multiple(width_in_blocks, width_alignment)
            data = data.reshape((-1, aligned_width, texel_pitch))
            data = data[y, x]
        return data.ravel()

    # from xgraphics.h from Xbox 360 XDK
    def XGAddress2DTiledOffset(x, y, Width, TexelPitch):
        AlignedWidth = (Width + 31) & ~31
        LogBpp = (TexelPitch >> 2) + ((TexelPitch >> 1) >> (TexelPitch >> 2))
        Macro = ((x >> 5) + (y >> 5) * (AlignedWidth >> 5)) << (LogBpp + 7)
        Micro = (((x & 7) + ((y & 6) << 2)) << LogBpp)
        Offset = Macro + ((Micro & ~15) << 1) + (Micro & 15) + ((y & 8) << (3 + LogBpp)) + ((y & 1) << 4)

        return (((Offset & ~511) << 3) + ((Offset & 448) << 2) + (Offset & 63) + ((y & 16) << 7) + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6)) >> LogBpp

    def get_linear_mips(data: np.ndarray, d3d_format: int, width: int, height: int, levels: int, tiles: list):
        mips = []
        address = 0

        tail_level = Deswizzler.get_tail_level(width, height)
        tail_levels = levels - tail_level
        has_tail = levels != 1 and tail_levels > 0
        head_tiles = tiles[:tail_level] if has_tail else tiles
        for tile_info in head_tiles:
            w, h, cw, ch, size = tile_info
            mip_data = data[address:address + size]
            address += size
            mips.append((mip_data, w, h, 0, 0, cw, ch))

        if has_tail:
            w, h, cw, ch, size = tiles[tail_level]
            tail_mips = Deswizzler.get_tail_mips(d3d_format, w, h, cw, ch, tail_levels)
            mip_data = data[address:address + size]
            address += size
            for tail_mip_info in tail_mips:
                mips.append((mip_data, *tail_mip_info))

        linear_mips = []
        for mip_info in mips:
            d, w, h, x, y, cw, _ = mip_info
            linear_data = Deswizzler.get_linear_data(d, d3d_format, w, h, x, y, cw)
            linear_mips.append(linear_data)
        return linear_mips
