from utils.forza_version import ForzaVersion
from models.forza_track_section import ForzaTrackSection

class RmbBin:
    def __init__(self, filepath: str):
        self.forza_version: ForzaVersion = ForzaVersion.Unknown
        self.filepath = filepath
        self.track_sections = []

    def get_objects_from_rmbbin(self):
        with open(self.filepath, "rb") as f:
            num = int.from_bytes(f.read(4), byteorder="big", signed=False)

            if num == 4:
                self.forza_version = ForzaVersion.FM3
            if num == 6:
                self.forza_version = ForzaVersion.FM4

            f.read(112)

            section_count: int = int.from_bytes(f.read(4), byteorder="big", signed=False)

            for i in section_count:
                self.track_sections.append(ForzaTrackSection)

