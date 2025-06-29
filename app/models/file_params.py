from dataclasses import dataclass
from typing import Union, Optional, TextIO, BinaryIO

from pydantic import BaseModel


class FileDataModel(BaseModel):
    file_name: str = ""
    file_format: str = ""
    file_base64: str = ""
    file_raw: str = ""
    file_url: str = ""
    file_path: str = ""

    def is_empty(self) -> bool:
        return not any([self.file_name, self.file_base64, self.file_raw, self.file_url, self.file_path])

@dataclass
class FileConvertParams:
    convert_type: str
    is_text: bool
    input_path: str = ""
    input_raw: Optional[Union[str, bytes, TextIO, BinaryIO]] = None

@dataclass
class FileStreamOrData:
    pass
