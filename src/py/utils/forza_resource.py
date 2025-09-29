import os
import io
import uuid
from typing import Optional
from utils.forza_version import ForzaVersion

class ForzaResource():
    def __init__(self, file_path: str, archive_path: str = None) -> None:
        if file_path is None:
            raise ValueError("A file path must be specified")

        self.id: uuid.UUID = uuid.uuid4()

        self.version: ForzaVersion = ForzaVersion.Unknown
        self._file_path: str = file_path.lower()
        self._archive_path: Optional[str] = archive_path.lower() if archive_path is not None else None

        self.name: Optional[str] = None

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def archive_path(self) -> Optional[str]:
        return self._archive_path

    @property
    def file_name(self) -> str:
        base = os.path.basename(self._file_path)
        name, _ext = os.path.splitext(base)
        return name.lower()

    @property
    def extension(self) -> str:
        _base = os.path.basename(self._file_path)
        _name, ext = os.path.splitext(_base)
        return ext.lower()

    def get_data(self) -> bytes:
        with open(self._file_path, "rb") as f:
            return f.read()
    
        return None

    def get_data_stream(self) -> io.BytesIO:
        data = self.get_data()
        return io.BytesIO(data) if data is not None else None