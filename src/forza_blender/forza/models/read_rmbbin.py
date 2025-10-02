from ..utils.forza_version import ForzaVersion
from .forza_track_section import ForzaTrackSection

class RmbBin:
    def __init__(self, path_file):
        self.forza_version: ForzaVersion = ForzaVersion.Unknown
        self.path_file = path_file
        self.track_sections = []

    def populate_objects_from_rmbbin(self):
        with self.path_file.open('rb') as f:
            _ = f.read(4)

            # TODO 
            # "int.from_bytes is made for a different thing. 
            # To parse file types from binary, struct.unpack is preferred" - Doliman100
            num = int.from_bytes(_, byteorder="big", signed=False)

            if num == 4:
                self.forza_version = ForzaVersion.FM3
            elif num == 6:
                self.forza_version = ForzaVersion.FM4

            f.read(112)

            section_count: int = int.from_bytes(f.read(4), byteorder="big", signed=False)

            for i in range(section_count):
                self.track_sections.append(ForzaTrackSection(f, self.forza_version))

