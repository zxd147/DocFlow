import time
from typing import Any
from typing import Optional, Union, Dict, Literal

from pydantic import BaseModel
from pydantic import Field


class FileDataRequest(BaseModel):
    file_url: str = ""
    file_path: str = ""
    file_name: str = ""
    file_base64: str = ""
    file_format: str = ""

    def is_empty(self) -> bool:
        return not any([self.file_url, self.file_path, self.file_base64, self.file_name])

class FileRequestModel(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_type: Literal["path", "file"] = "path"
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileUploadRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_type: Literal["path", "file"] = "path"
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileDownloadRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_type: Literal["path", "file"] = "path"
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileExtractRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_type: Literal["path", "file"] = "path"
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

class FileConvertRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = True
    return_base64: bool = False
    return_type: Literal["path", "file"] = "path"
    extra: Dict[str, Any] = ""
    data: Optional[FileDataRequest] = []

