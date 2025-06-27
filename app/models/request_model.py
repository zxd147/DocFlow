import time
from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, Field


class FileDataRequest(BaseModel):
    file_name: str = ""
    file_format: str = ""
    file_base64: str = ""
    file_raw: str = ""
    file_url: str = ""
    file_path: str = ""

    def is_empty(self) -> bool:
        return not any([self.file_name, self.file_base64, self.file_text, self.file_url, self.file_path])

class FileModelRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = False
    return_base64: bool = False
    return_raw: bool = False
    return_file: bool = False
    extra: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[FileDataRequest] = Field(default_factory=FileDataRequest)



