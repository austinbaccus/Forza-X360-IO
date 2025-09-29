from read_bix import Bix
from PIL import Image

if "__main__":
    # examples of images with different formats:
    # dxt5  --> r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x00000A5E.bix"
    # dxt1  --> r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x0000021A.bix"
    # dxt5a --> r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x0000020E.bix"
    # dxn   --> r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x00000345.bix"
    Bix.save_image_from_bix(r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x00000A5E.bix")
    Bix.save_image_from_bix(r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x0000021A.bix")
    Bix.save_image_from_bix(r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x0000020E.bix")
    Bix.save_image_from_bix(r"X:\3d\games\forza\games\fm3\fm3_d1\fm3\Media\Tracks\_decompressed\Amalfi\bin\_0x00000345.bix")