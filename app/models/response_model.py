from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, Field

from app.models.file_conversion import FileDataModel


class FileModelResponse(BaseModel):
    sno: Optional[Union[int, str]] = None
    uid: Optional[Union[int, str]] = None
    code: int
    messages: str
    extra: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[FileDataModel] = Field(default_factory=FileDataModel)


