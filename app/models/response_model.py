from typing import Optional, Union

from pydantic import BaseModel, Field

class FileDataResponse(BaseModel):
    file_name: str = ""
    file_format: str = ""
    file_base64: str = ""
    file_url: str = ""
    file_path: str = ""
    file_text: str = ""

class FileModelResponse(BaseModel):
    uid: Optional[Union[int, str]] = None
    sno: Optional[Union[int, str]] = None
    code: int
    messages: str
    data: Optional[FileDataResponse] = Field(default_factory=FileDataResponse)

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

