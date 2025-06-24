from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel


class FileDataResponse(BaseModel):
    file_url: str = ""
    file_path: str = ""
    file_name: str = ""
    file_base64: str = ""
    file_format: str = ""

class FileResponseModel(BaseModel):
    uid: str
    sno: str
    code: int = 0
    messages: Optional[str]
    data: Optional[FileDataResponse] = []

class FileUploadResponse(BaseModel):
    uid: str
    sno: str
    code: int = 0
    messages: Optional[str]
    data: Optional[FileDataResponse] = []

class FileDownloadResponse(BaseModel):
    uid: str
    sno: Union[int, str] = None
    code: int = 0
    messages: Optional[str]
    data: Optional[FileDataResponse] = []

class FileExtractResponse(BaseModel):
    uid: str
    sno: Union[int, str] = None
    code: int = 0
    messages: Optional[str]
    data: Optional[FileDataResponse] = []

class FileConvertResponse(BaseModel):
    uid: str
    sno: Union[int, str] = None
    code: int = 0
    messages: Optional[str]
    data: Optional[FileDataResponse] = []

