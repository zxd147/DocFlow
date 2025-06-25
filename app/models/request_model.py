import time
from typing import Any
from typing import Optional, Union, Dict

from pydantic import BaseModel
from pydantic import Field


class FileDataRequest(BaseModel):
    file_name: str = ""
    file_format: str = ""
    file_base64: str = ""
    file_url: str = ""
    file_path: str = ""

    def is_empty(self) -> bool:
        return not any([self.file_url, self.file_path, self.file_base64, self.file_name])

class FileModelRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = False
    return_base64: bool = False
    return_text: bool = False
    return_file: bool = False
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileUploadRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_file: bool = False
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileDownloadRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_file: bool = False
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileExtractRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_file: bool = False
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileConvertRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_file: bool = False
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

