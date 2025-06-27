from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, Field


class FileDataResponse(BaseModel):
    file_name: str = ""
    file_format: str = ""
    file_base64: str = ""
    file_raw: str = ""
    file_url: str = ""
    file_path: str = ""

class FileModelResponse(BaseModel):
    sno: Optional[Union[int, str]] = None
    uid: Optional[Union[int, str]] = None
    code: int
    messages: str
    extra: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[FileDataResponse] = Field(default_factory=FileDataResponse)


