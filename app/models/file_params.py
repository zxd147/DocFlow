from dataclasses import dataclass
from typing import Union, Optional, TextIO, BinaryIO


@dataclass
class FileConvertParams:
    convert_type: str
    is_text: bool
    input_path: str = ""
    input_raw: Optional[Union[str, bytes, TextIO, BinaryIO]] = None

@dataclass
class FileStreamOrData:
    pass
