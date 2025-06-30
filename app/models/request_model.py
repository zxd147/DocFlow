import time
from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, Field

from app.models.file_conversion import FileDataModel


class FileModelRequest(BaseModel):
    sno: Union[int, str] = Field(default_factory=lambda: int(time.time() * 100))
    uid: Optional[Union[int, str]] = 'null'
    do_save: bool = False
    return_base64: bool = False
    return_raw: bool = False
    return_stream: bool = False
    extra: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[FileDataModel] = Field(default_factory=FileDataModel)



