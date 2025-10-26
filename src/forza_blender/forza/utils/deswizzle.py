import numpy as np

class Deswizzler:
    def XGUntileSurfaceToLinearTexture(data, width, height, textureTypeStr, levels):
        blockSize = 0
        texelPitch = 0

        if textureTypeStr == "DXT1":
            blockSize = 4
            texelPitch = 8
        elif textureTypeStr == "DXT5":
            blockSize = 4
            texelPitch = 16
        elif textureTypeStr == "UNC":
            blockSize = 2;
            texelPitch = 4;
        elif textureTypeStr == "CTX1":
            blockSize = 4;
            texelPitch = 8;
        elif textureTypeStr == "8_8_8_8":
            blockSize = 1
            texelPitch = 4
        else:
            print("Bad dxt type!")
            return 0

        offset_x = 0
        offset_y = 0
        if levels != 1 and (width <= 16 or height <= 16):
            if width <= height:
                offset_x = 16 // blockSize
            else:
                offset_y = 16 // blockSize

        blockWidth = (width + blockSize - 1) // blockSize
        blockHeight = (height + blockSize - 1) // blockSize

        x, y = np.meshgrid(np.arange(offset_x, offset_x + blockWidth), np.arange(offset_y, offset_y + blockHeight))
        srcOffset = Deswizzler.XGAddress2DTiledOffset(x, y, blockWidth, texelPitch)
        data = data.reshape((-1, texelPitch))
        return data[srcOffset]

    # from xgraphics.h from Xbox 360 XDK
    def XGAddress2DTiledOffset(x, y, Width, TexelPitch):
        AlignedWidth = (Width + 31) & ~31
        LogBpp = (TexelPitch >> 2) + ((TexelPitch >> 1) >> (TexelPitch >> 2))
        Macro = ((x >> 5) + (y >> 5) * (AlignedWidth >> 5)) << (LogBpp + 7)
        Micro = (((x & 7) + ((y & 6) << 2)) << LogBpp)
        Offset = Macro + ((Micro & ~15) << 1) + (Micro & 15) + ((y & 8) << (3 + LogBpp)) + ((y & 1) << 4)

        return (((Offset & ~511) << 3) + ((Offset & 448) << 2) + (Offset & 63) + ((y & 16) << 7) + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6)) >> LogBpp
