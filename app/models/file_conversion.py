from dataclasses import dataclass
from enum import Enum
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
    return_img: bool = False
    input_path: str = ""
    input_raw: Optional[Union[str, bytes, TextIO, BinaryIO]] = None
    input_stream: Optional[Union[str, bytes, TextIO, BinaryIO]] = None
    output_path: str = ""

class ConvertType(str, Enum):
    pdf2docx = "pdf2docx"
    docx2html = "docx2html"
    pdf2html = "pdf2html"
    html2docx = "html2docx"
    docx2pdf = "docx2pdf"
    html2pdf = "html2pdf"
    csv2xlsx = "csv2xlsx"
    csv2html = "csv2html"
    csv2md = "csv2md"
    xls2xlsx = "xls2xlsx"
    xls2html = "xls2html"
    xls2md = "xls2md"
    xlsx2csv = "xlsx2csv"
    xlsx2html = "xlsx2html"
    xlsx2md = "xlsx2md"
    html2xlsx = "html2xlsx"
    html2csv = "html2csv"
    html2md = "html2md"
    md2xlsx = "md2xlsx"
    md2html = "md2html"
    # 将来新增支持类型：md2html, xls2csv, 等等

